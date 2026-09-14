import os
import threading
from pathlib import Path
from tkinter import Button, Entry, Frame, Label, StringVar, TclError, Tk, messagebox

from dotenv import dotenv_values, load_dotenv, set_key


_BASE_DIR = Path(__file__).resolve().parent
_ENV_PATH = _BASE_DIR / ".env"
_PLACEHOLDER_EMAILS = {
    "",
    "your_email@gmail.com",
    "admin@example.com",
    "your_email@example.com",
}
_PLACEHOLDER_PASSWORDS = {
    "",
    "your_app_password_here",
    "change-me",
    "your_password_here",
}


def _read_email_config() -> tuple[str, str]:
    values = dotenv_values(_ENV_PATH) if _ENV_PATH.exists() else {}
    email_address = (values.get("EMAIL_ADDRESS") or os.getenv("EMAIL_ADDRESS") or "").strip()
    email_password = (values.get("EMAIL_PASSWORD") or os.getenv("EMAIL_PASSWORD") or "").strip()
    return email_address, email_password


def _email_configured() -> bool:
    email_address, email_password = _read_email_config()
    if email_address.lower() in _PLACEHOLDER_EMAILS:
        return False
    if email_password in _PLACEHOLDER_PASSWORDS:
        return False
    if email_address.startswith("your_") or email_password.startswith("your_"):
        return False
    return "@" in email_address


def _save_email_config(email_address: str, email_password: str) -> None:
    _ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _ENV_PATH.exists():
        _ENV_PATH.touch()
    set_key(str(_ENV_PATH), "EMAIL_ADDRESS", email_address)
    set_key(str(_ENV_PATH), "EMAIL_PASSWORD", email_password)


def _prompt_for_email_setup() -> bool:
    try:
        root = Tk()
    except TclError:
        print(
            "[email_setup] Could not open the local setup window. "
            "Set EMAIL_ADDRESS and EMAIL_PASSWORD in client_agent/.env to enable email scanning."
        )
        return False

    root.title("Defendra.AI Email Setup")
    root.geometry("560x340")
    root.minsize(560, 340)
    root.resizable(False, False)

    current_email, current_password = _read_email_config()
    email_var = StringVar(value=current_email)
    password_var = StringVar(value=current_password)
    status_var = StringVar(
        value="Enter the company Gmail address and Gmail App Password. The app will save it locally and configure IMAP automatically."
    )

    container = Frame(root, padx=18, pady=18)
    container.pack(fill="both", expand=True)

    Label(container, text="Email Scanner Setup", font=("Segoe UI", 15, "bold")).pack(anchor="w")
    Label(
        container,
        text="Only the email address and Gmail App Password are required. The scanner uses Gmail IMAP automatically.",
        wraplength=520,
        justify="left",
    ).pack(anchor="w", pady=(8, 14))

    form = Frame(container)
    form.pack(fill="x")

    Label(form, text="Email address").grid(row=0, column=0, sticky="w", pady=(0, 6))
    email_entry = Entry(form, textvariable=email_var, width=48)
    email_entry.grid(row=1, column=0, sticky="ew", pady=(0, 12))

    Label(form, text="Email password / app password").grid(row=2, column=0, sticky="w", pady=(0, 6))
    password_entry = Entry(form, textvariable=password_var, show="*", width=48)
    password_entry.grid(row=3, column=0, sticky="ew")

    form.columnconfigure(0, weight=1)

    Label(
        container,
        text="Tip: for Gmail, use a Google App Password instead of the normal account password.",
        foreground="#666666",
        wraplength=520,
        justify="left",
    ).pack(anchor="w", pady=(12, 8))

    Label(container, textvariable=status_var, wraplength=520, justify="left", foreground="#004d40").pack(
        anchor="w", pady=(0, 12)
    )

    button_row = Frame(container)
    button_row.pack(fill="x", pady=(6, 0))

    result = {"saved": False}

    def save_and_close() -> None:
        email_address = email_var.get().strip()
        email_password = password_var.get().strip()
        if not email_address or not email_password:
            status_var.set("Both fields are required.")
            return
        if "@" not in email_address:
            status_var.set("Enter a valid email address.")
            return
        try:
            _save_email_config(email_address, email_password)
            load_dotenv(dotenv_path=_ENV_PATH, override=True)
            result["saved"] = True
            root.destroy()
        except OSError as exc:
            messagebox.showerror("Could not save email settings", str(exc))

    def skip_setup() -> None:
        result["saved"] = False
        root.destroy()

    Button(button_row, text="Save and continue", command=save_and_close).pack(side="right")
    Button(button_row, text="Skip for now", command=skip_setup).pack(side="right", padx=(0, 8))

    email_entry.focus_set()
    root.mainloop()
    return result["saved"]


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

    if not _email_configured():
        print("[email_setup] Opening first-run email setup window...")
        _prompt_for_email_setup()

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