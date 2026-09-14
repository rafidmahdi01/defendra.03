import json
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# Base URL of the Defendra backend, e.g. http://127.0.0.1:8000
MARIA_API_URL = os.getenv("MARIA_API_URL", "http://127.0.0.1:8000")
# JWT token obtained from POST /api/auth/login — paste the access_token here
MARIA_API_TOKEN = os.getenv("MARIA_API_TOKEN", "")
DEVICE_NAME = os.getenv("DEVICE_NAME", "PC-KANIJ")

_BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = _BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

THREATS_LOG = LOGS_DIR / "threats.log"
OFFLINE_ALERTS_FILE = LOGS_DIR / "offline_alerts.json"

_retry_lock = threading.Lock()
_retry_thread_running = False


def log_threat(message: str) -> None:
    """Append a timestamped line to logs/threats.log."""
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"[{timestamp}] {message}\n"
    print(f"[alert_sender] THREAT: {message}")
    try:
        with open(THREATS_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        print(f"[alert_sender] Failed to write threat log: {e}")


def send_alert(
    alert_type: str,
    severity: str,
    details: str,
    device: str = DEVICE_NAME,
) -> bool:
    """
    Send a threat alert to Defendra's FastAPI backend (POST /api/alerts).

    Maps client_agent fields onto Defendra's AlertCreate schema:
      alert_type -> title + rule_name
      details    -> description
      severity   -> severity (low / medium / high / critical)

    Requires MARIA_API_TOKEN in .env (JWT from POST /api/auth/login).

    If the backend is unreachable the alert is saved to logs/offline_alerts.json
    and a background thread retries after 60 seconds.
    """
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


_cached_token = None
_token_obtained_at = 0

def _get_or_refresh_token() -> str:
    """Get JWT token from backend, using cache to avoid repeated logins."""
    global _cached_token, _token_obtained_at
    
    now = time.time()
    # Refresh token every 50 minutes (tokens are typically 1 hour)
    if _cached_token and (now - _token_obtained_at) < 3000:
        return _cached_token
    
    backend_email = os.getenv("BACKEND_EMAIL", "")
    backend_password = os.getenv("BACKEND_PASSWORD", "")
    
    if not backend_email or not backend_password:
        return MARIA_API_TOKEN or ""
    
    try:
        resp = requests.post(
            f"{MARIA_API_URL}/api/auth/login",
            json={"email": backend_email, "password": backend_password},
            timeout=5,
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token", "")
            _cached_token = token
            _token_obtained_at = now
            return token
    except Exception as e:
        print(f"[alert_sender] Token refresh failed: {e}")
    
    return MARIA_API_TOKEN or ""


def _build_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    token = _get_or_refresh_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _build_payload(alert_type: str, severity: str, details: str) -> dict:
    """Map detection fields to Defendra's AlertCreate Pydantic schema."""
    from utils.device_manager import get_device_id  # lazy import — avoids circular deps

    payload: dict = {
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
    """Persist an undelivered alert to logs/offline_alerts.json."""
    entry = {
        "type": alert_type,
        "severity": severity,
        "details": details,
        "device": device,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    existing: list = []
    if OFFLINE_ALERTS_FILE.exists():
        try:
            with open(OFFLINE_ALERTS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []
    existing.append(entry)
    try:
        with open(OFFLINE_ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except OSError as e:
        print(f"[alert_sender] Failed to save offline alert: {e}")


def _flush_offline_alerts() -> None:
    """Attempt to POST all pending offline alerts to the backend."""
    global _retry_thread_running

    if not OFFLINE_ALERTS_FILE.exists():
        _retry_thread_running = False
        return

    try:
        with open(OFFLINE_ALERTS_FILE, "r", encoding="utf-8") as f:
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
            with open(OFFLINE_ALERTS_FILE, "w", encoding="utf-8") as f:
                json.dump(remaining, f, indent=2)
        else:
            OFFLINE_ALERTS_FILE.unlink(missing_ok=True)
    except OSError:
        pass

    _retry_thread_running = False


def _retry_offline_alerts_background() -> None:
    """Fire-and-forget flush of any saved offline alerts."""
    if OFFLINE_ALERTS_FILE.exists():
        t = threading.Thread(
            target=_flush_offline_alerts,
            daemon=True,
            name="offline-flush",
        )
        t.start()


def _start_retry_thread() -> None:
    """Spawn a single background thread that waits 60 s then retries offline alerts."""
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
