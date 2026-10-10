import json
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

import requests

from utils.config import get_data_dir, load_all_configs

load_all_configs()

MARIA_API_URL = os.getenv("MARIA_API_URL", os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))
MARIA_API_TOKEN = os.getenv("MARIA_API_TOKEN", os.getenv("ENROLLMENT_TOKEN", ""))
DEVICE_NAME = os.getenv("DEVICE_NAME", "Defendra-Endpoint")


def _get_threats_log() -> Path:
    logs_dir = get_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / "threats.log"


def _get_offline_alerts_file() -> Path:
    logs_dir = get_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / "offline_alerts.json"


_retry_lock = threading.Lock()
_retry_thread_running = False


def log_threat(message: str) -> None:
    """Append a timestamped line to logs/threats.log."""
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"[{timestamp}] {message}\n"
    print(f"[alert_sender] THREAT: {message}")
    try:
        with open(_get_threats_log(), "a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        print(f"[alert_sender] Failed to write threat log: {e}")


def _build_headers() -> dict:
    from utils.device_manager import _get_token
    token = _get_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _build_payload(alert_type: str, severity: str, details: str) -> dict:
    from utils.device_manager import get_device_id
    payload = {
        "title": alert_type.replace("_", " ").title(),
        "description": details,
        "severity": severity,
        "status": "open",
        "rule_name": alert_type,
    }
    device_id = get_device_id()
    if device_id is not None:
        payload["device_id"] = device_id
    return payload


def _save_offline(alert_type: str, severity: str, details: str, device: str) -> None:
    entry = {
        "type": alert_type,
        "severity": severity,
        "details": details,
        "device": device,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    offline_file = _get_offline_alerts_file()
    existing: list = []
    if offline_file.exists():
        try:
            with open(offline_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []
    existing.append(entry)
    try:
        with open(offline_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except OSError as e:
        print(f"[alert_sender] Failed to save offline alert: {e}")


def _flush_offline_alerts() -> None:
    global _retry_thread_running
    offline_file = _get_offline_alerts_file()
    if not offline_file.exists():
        _retry_thread_running = False
        return

    try:
        with open(offline_file, "r", encoding="utf-8") as f:
            alerts = json.load(f)
    except (json.JSONDecodeError, OSError):
        _retry_thread_running = False
        return

    remaining = []
    headers = _build_headers()

    for alert in alerts:
        payload = _build_payload(
            alert.get("type", "unknown"),
            alert.get("severity", "low"),
            alert.get("details", ""),
        )
        try:
            resp = requests.post(
                f"{MARIA_API_URL}/api/alerts",
                json=payload,
                headers=headers,
                timeout=10,
            )
            if resp.status_code not in (200, 201):
                remaining.append(alert)
        except requests.RequestException:
            remaining.append(alert)

    try:
        if remaining:
            with open(offline_file, "w", encoding="utf-8") as f:
                json.dump(remaining, f, indent=2)
        else:
            offline_file.unlink(missing_ok=True)
    except OSError:
        pass

    _retry_thread_running = False


def _retry_offline_alerts_background() -> None:
    if _get_offline_alerts_file().exists():
        t = threading.Thread(
            target=_flush_offline_alerts,
            daemon=True,
            name="offline-flush",
        )
        t.start()


def _start_retry_thread() -> None:
    global _retry_thread_running
    with _retry_lock:
        if _retry_thread_running:
            return
        _retry_thread_running = True

    def _worker():
        time.sleep(60)
        _flush_offline_alerts()

    t = threading.Thread(target=_worker, daemon=True, name="offline-alert-retry")
    t.start()


def send_alert(
    alert_type: str,
    severity: str,
    details: str,
    device: str = DEVICE_NAME,
) -> bool:
    payload = _build_payload(alert_type, severity, details)
    headers = _build_headers()

    _retry_offline_alerts_background()

    try:
        resp = requests.post(
            f"{MARIA_API_URL}/api/alerts",
            json=payload,
            headers=headers,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True
        else:
            log_threat(
                f"Backend returned HTTP {resp.status_code} for alert "
                f"type={alert_type}: {details}"
            )
            _save_offline(alert_type, severity, details, device)
            _start_retry_thread()
            return False

    except requests.RequestException as e:
        log_threat(f"Backend unreachable ({e}), alert saved offline. type={alert_type}")
        _save_offline(alert_type, severity, details, device)
        _start_retry_thread()
        return False
