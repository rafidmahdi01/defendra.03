import json
import os
import platform
import socket
import threading
import time
import uuid
from pathlib import Path

import psutil
import requests

from scan_config import SCAN_INTERVAL_SECONDS
from utils.config import get_data_dir, load_all_configs

load_all_configs()

MARIA_API_URL = os.getenv("MARIA_API_URL", os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))
MARIA_API_TOKEN = os.getenv("MARIA_API_TOKEN", os.getenv("ENROLLMENT_TOKEN", ""))
BACKEND_EMAIL = os.getenv("BACKEND_EMAIL", "")
BACKEND_PASSWORD = os.getenv("BACKEND_PASSWORD", "")
DEVICE_NAME = os.getenv("DEVICE_NAME", socket.gethostname())
AGENT_VERSION = "1.0.0"

_cached_token: str | None = None
_token_obtained_at: float = 0

_device_id: str | None = None
_device_lock = threading.Lock()


def _get_device_id_file() -> Path:
    logs_dir = get_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / "device_id.txt"


def _get_token() -> str:
    global _cached_token, _token_obtained_at
    now = time.time()
    if _cached_token and (now - _token_obtained_at) < 3000:
        return _cached_token
    if BACKEND_EMAIL and BACKEND_PASSWORD:
        try:
            resp = requests.post(
                f"{MARIA_API_URL}/api/auth/login",
                json={"email": BACKEND_EMAIL, "password": BACKEND_PASSWORD},
                timeout=5,
            )
            if resp.status_code == 200:
                token = resp.json().get("access_token", "")
                _cached_token = token
                _token_obtained_at = now
                return token
        except Exception as e:
            print(f"[device_manager] Login failed: {e}")
    return MARIA_API_TOKEN or ""


def _build_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    token = _get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def sync_email_scanner_settings() -> bool:
    token = _get_token()
    if not token:
        return False
    try:
        resp = requests.get(
            f"{MARIA_API_URL}/api/auth/me/email-scanner-settings/secret",
            headers=_build_headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            return False
        data = resp.json() or {}
        email_address = (data.get("email_address") or "").strip()
        email_password = (data.get("email_password") or "").strip()
        if not email_address or not email_password:
            return False
        
        env_path = get_data_dir() / ".env"
        env_lines = []
        if env_path.exists():
            env_lines = env_path.read_text(encoding="utf-8").splitlines()

        def _replace_or_append(lines: list[str], key: str, value: str) -> list[str]:
            prefix = f"{key}="
            out = []
            replaced = False
            for line in lines:
                if line.startswith(prefix):
                    out.append(f"{key}={value}")
                    replaced = True
                else:
                    out.append(line)
            if not replaced:
                out.append(f"{key}={value}")
            return out

        env_lines = _replace_or_append(env_lines, "EMAIL_ADDRESS", email_address)
        env_lines = _replace_or_append(env_lines, "EMAIL_PASSWORD", email_password)
        env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"[device_manager] Could not sync email settings: {e}")
        return False


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _get_mac_address() -> str:
    try:
        raw_mac = uuid.getnode()
        mac_hex = f"{raw_mac:012x}"
        return ":".join(mac_hex[i:i+2] for i in range(0, 12, 2)).upper()
    except Exception:
        return "00:00:00:00:00:00"


def _read_cached_id() -> str | None:
    id_file = _get_device_id_file()
    if not id_file.exists():
        return None
    try:
        raw = id_file.read_text(encoding="utf-8").strip()
        return raw if raw else None
    except OSError:
        return None


def _save_cached_id(device_id: str) -> None:
    id_file = _get_device_id_file()
    try:
        id_file.write_text(str(device_id).strip(), encoding="utf-8")
    except OSError as e:
        print(f"[device_manager] Failed to save device_id: {e}")


def _clear_cached_id() -> None:
    global _device_id
    _device_id = None
    id_file = _get_device_id_file()
    try:
        id_file.unlink(missing_ok=True)
    except OSError:
        pass


def get_device_id() -> str | None:
    global _device_id
    with _device_lock:
        if _device_id:
            return _device_id
        cached = _read_cached_id()
        if cached:
            _device_id = cached
            return _device_id
    return None


def register_or_get_device() -> str | None:
    global _device_id
    with _device_lock:
        existing = _read_cached_id()
        if existing:
            _device_id = existing
            return _device_id

        payload = {
            "name": DEVICE_NAME,
            "ip_address": _get_local_ip(),
            "mac_address": _get_mac_address(),
            "os_name": f"{platform.system()} {platform.release()}",
            "agent_version": AGENT_VERSION,
        }

        try:
            resp = requests.post(
                f"{MARIA_API_URL}/api/devices",
                json=payload,
                headers=_build_headers(),
                timeout=10,
            )
            if resp.status_code in (200, 201):
                body = resp.json()
                raw_id = body.get("id")
                if raw_id is not None:
                    _device_id = str(raw_id)
                    _save_cached_id(_device_id)
                    print(f"[device_manager] Registered as device_id={_device_id}")
                    return _device_id
            print(f"[device_manager] Registration response status {resp.status_code}")
        except requests.RequestException as e:
            print(f"[device_manager] Registration skipped (backend unreachable): {e}")

    return None


def send_heartbeat() -> bool:
    device_id = get_device_id()
    if device_id is None:
        device_id = register_or_get_device()
    if device_id is None:
        return False

    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
    except Exception:
        cpu, ram = 0.0, 0.0

    payload = {"status": "online", "cpu_usage": cpu, "ram_usage": ram}

    try:
        resp = requests.post(
            f"{MARIA_API_URL}/api/devices/{device_id}/heartbeat",
            json=payload,
            headers=_build_headers(),
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True
        if resp.status_code == 404:
            _clear_cached_id()
            new_id = register_or_get_device()
            if new_id:
                retry = requests.post(
                    f"{MARIA_API_URL}/api/devices/{new_id}/heartbeat",
                    json=payload,
                    headers=_build_headers(),
                    timeout=10,
                )
                return retry.status_code in (200, 201)
        return False
    except requests.RequestException:
        return False


def run_heartbeat_loop(interval: int = SCAN_INTERVAL_SECONDS) -> None:
    print(f"[device_manager] Heartbeat loop started (interval={interval}s).")
    while True:
        send_heartbeat()
        time.sleep(interval)
