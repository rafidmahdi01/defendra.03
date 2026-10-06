import os
import threading
from pathlib import Path

from dotenv import load_dotenv


_BASE_DIR = Path(__file__).resolve().parent
_ENV_PATH = _BASE_DIR / ".env"


# Removed legacy functions:
# - _read_email_config: credentials should not be read from plaintext files
# - _email_configured: email scanner now expects tokens passed in-memory
# - _save_email_config: no more writing credentials to disk
# - _prompt_for_email_setup: OAuth 2.0 flow replaces Tkinter password prompts


def ensure_directories():
    os.makedirs(_BASE_DIR / "logs", exist_ok=True)
    os.makedirs(_BASE_DIR / "quarantine", exist_ok=True)

    threats_log = _BASE_DIR / "logs" / "threats.log"
    if not threats_log.exists():
        threats_log.touch()


if __name__ == "__main__":
    print("Starting Defendra.AI - Detection Layer...")
    os.chdir(_BASE_DIR)
    ensure_directories()

    # Legacy email setup removed - email scanner now uses OAuth 2.0 tokens
    # passed in-memory from the backend instead of plaintext credentials
    load_dotenv(dotenv_path=_ENV_PATH, override=True)

    from behavior_monitor import run_behavior_monitor
    from email_scanner import run_email_scanner
    from system_scanner import run_system_scanner
    from usb_scanner import run_usb_scanner
    from utils.device_manager import register_or_get_device, run_heartbeat_loop, sync_email_scanner_settings

    # Register this device with the Defendra backend (idempotent — reads from
    # logs/device_id.txt on subsequent runs so no duplicate devices are created).
    device_id = register_or_get_device()
    if device_id:
        print(f"Connected to Defendra backend as device_id={device_id}")
    else:
        print("Warning: Could not register with backend. Alerts will still be sent without device linkage.")

    sync_email_scanner_settings()

    threads = [
        threading.Thread(target=run_email_scanner, daemon=True, name="email-scanner"),
        threading.Thread(target=run_usb_scanner, daemon=True, name="usb-scanner"),
        threading.Thread(target=run_behavior_monitor, daemon=True, name="behavior-monitor"),
        threading.Thread(target=run_heartbeat_loop, daemon=True, name="heartbeat"),
        # Runs a full system scan on startup, then every 6 hours
        threading.Thread(target=run_system_scanner, daemon=True, name="system-scanner"),
    ]

    for t in threads:
        t.start()

    try:
        # Keep the main thread alive so daemon threads continue running
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("Shutting down Detection Layer...")