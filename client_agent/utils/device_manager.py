import os
import platform
import socket
import threading
import time
import uuid
from pathlib import Path

import psutil
import requests
from dotenv import load_dotenv

from scan_config import SCAN_INTERVAL_SECONDS

_BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_BASE_DIR / ".env")

MARIA_API_URL = os.getenv("MARIA_API_URL", "http://127.0.0.1:8000")
MARIA_API_TOKEN = os.getenv("MARIA_API_TOKEN", "")
BACKEND_EMAIL = os.getenv("BACKEND_EMAIL", "")
BACKEND_PASSWORD = os.getenv("BACKEND_PASSWORD", "")
DEVICE_NAME = os.getenv("DEVICE_NAME", socket.gethostname())
AGENT_VERSION = "1.0.0"

_cached_token: str | None = None
_token_obtained_at: float = 0

_DEVICE_ID_FILE = _BASE_DIR / "logs" / "device_id.txt"

_device_id: str | None = None
_device_lock = threading.Lock()


# ── helpers ──────────────────────────────────────────────────────────────────

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
        env_path = _BASE_DIR.parent / "client_agent" / ".env"
        env_path.parent.mkdir(parents=True, exist_ok=True)
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


def _get_mac_address() -> str | None:
    try:
        mac_int = uuid.getnode()
        mac_hex = f"{mac_int:012x}"
        return ":".join(mac_hex[i : i + 2] for i in range(0, 12, 2))
    except Exception:
        return None


def _load_cached_id() -> str | None:
    if _DEVICE_ID_FILE.exists():
        try:
            val = _DEVICE_ID_FILE.read_text(encoding="utf-8").strip()
            return val if val else None
        except OSError:
            return None
    return None


def _save_cached_id(device_id: str) -> None:
    try:
        _DEVICE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DEVICE_ID_FILE.write_text(str(device_id), encoding="utf-8")
    except OSError as e:
        print(f"[device_manager] Could not save device_id: {e}")


def _clear_cached_id() -> None:
    """Drop local device id when the backend no longer has that document (e.g. new Firebase project)."""
    global _device_id
    _device_id = None
    try:
        _DEVICE_ID_FILE.unlink(missing_ok=True)
    except OSError as e:
        print(f"[device_manager] Could not remove cached device_id: {e}")


# ── public API ────────────────────────────────────────────────────────────────

def get_device_id() -> str | None:
    """Return cached device_id without making any network requests."""
    global _device_id
    if _device_id is not None:
        return _device_id
    _device_id = _load_cached_id()
    return _device_id


def register_or_get_device() -> str | None:
    """
    Return this machine's Defendra device ID (Firestore document id string).

    Order of resolution:
      1. In-memory cache (fastest)
      2. logs/device_id.txt  (persisted across restarts)
      3. POST /api/devices   (first-time registration; requires admin JWT)
    """
    global _device_id

    with _device_lock:
        if _device_id is not None:
            return _device_id

        cached = _load_cached_id()
        if cached is not None:
            try:
                resp = requests.post(
                    f"{MARIA_API_URL}/api/devices/{cached}/heartbeat",
                    json={"status": "online", "cpu_usage": 0.0, "ram_usage": 0.0},
                    headers=_build_headers(),
                    timeout=10,
                )
                if resp.status_code in (200, 201):
                    _device_id = cached
                    print(f"[device_manager] Using cached device_id={_device_id}")
                    return _device_id
                if resp.status_code == 404:
                    print("[device_manager] Cached device_id not on server — re-registering...")
                    _clear_cached_id()
                else:
                    print(
                        f"[device_manager] Cached device verify HTTP {resp.status_code} — "
                        "keeping cache for retry"
                    )
                    _device_id = cached
                    return _device_id
            except requests.RequestException as e:
                print(f"[device_manager] Backend unreachable, using cached device_id={cached} ({e})")
                _device_id = cached
                return _device_id

        payload = {
            "hostname": DEVICE_NAME,
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
                if raw_id is None:
                    print("[device_manager] Registration response missing id")
                    return None
                _device_id = str(raw_id)
                _save_cached_id(_device_id)
                print(f"[device_manager] Registered as device_id={_device_id}")
                return _device_id
            print(
                f"[device_manager] Registration failed HTTP {resp.status_code}: "
                f"{resp.text[:200]}"
            )
        except requests.RequestException as e:
            print(f"[device_manager] Registration failed (backend unreachable): {e}")

    return None


def send_heartbeat() -> bool:
    """
    POST /api/devices/{id}/heartbeat with current CPU & RAM usage.

    Returns True on success, False on any failure.
    Re-registers automatically when the cached id is missing on the server (HTTP 404).
    """
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

    def _post_hb(target_id: str) -> requests.Response:
        return requests.post(
            f"{MARIA_API_URL}/api/devices/{target_id}/heartbeat",
            json=payload,
            headers=_build_headers(),
            timeout=10,
        )

    try:
        resp = _post_hb(device_id)
        if resp.status_code in (200, 201):
            return True
        if resp.status_code == 404:
            print(
                "[device_manager] Device not found on server (stale cache?) — re-registering..."
            )
            _clear_cached_id()
            new_id = register_or_get_device()
            if new_id is None:
                return False
            retry = _post_hb(new_id)
            if retry.status_code in (200, 201):
                print(f"[device_manager] Heartbeat restored for device_id={new_id}")
                return True
            print(f"[device_manager] Heartbeat HTTP {retry.status_code} after re-register")
            return False
        print(f"[device_manager] Heartbeat HTTP {resp.status_code}")
        return False
    except requests.RequestException as e:
        print(f"[device_manager] Heartbeat failed: {e}")
        return False


def run_heartbeat_loop(interval: int = SCAN_INTERVAL_SECONDS) -> None:
    """
    Blocking loop — call from a daemon thread in main.py.

    Sends a heartbeat every `interval` seconds so the backend keeps the
    device marked as 'online'.
    """
    print(f"[device_manager] Heartbeat loop started (interval={interval}s).")
    while True:
        send_heartbeat()
        time.sleep(interval)
