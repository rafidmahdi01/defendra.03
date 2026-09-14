import email
import imaplib
import os
import re
import time
from pathlib import Path

import requests
from dotenv import dotenv_values, load_dotenv

from scan_config import SCAN_INTERVAL_SECONDS
from utils.ai_analyzer import analyze_email_with_ai, analyze_threat, huggingface_configured
from utils.alert_sender import log_threat, send_alert
from utils.device_manager import sync_email_scanner_settings

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=_BASE_DIR / ".env")
VT_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

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

_last_auth_error_at = 0.0


def _read_email_credentials() -> tuple[str, str]:
    values = dotenv_values(_BASE_DIR / ".env") if (_BASE_DIR / ".env").exists() else {}
    email_address = (values.get("EMAIL_ADDRESS") or os.getenv("EMAIL_ADDRESS") or "").strip()
    email_password = (values.get("EMAIL_PASSWORD") or os.getenv("EMAIL_PASSWORD") or "").strip()
    return email_address, email_password


def email_scanner_configured() -> bool:
    """True when real Gmail IMAP credentials are set (not template placeholders)."""
    email_address, email_password = _read_email_credentials()
    if email_address.lower() in _PLACEHOLDER_EMAILS:
        return False
    if email_password in _PLACEHOLDER_PASSWORDS:
        return False
    if email_address.startswith("your_") or email_password.startswith("your_"):
        return False
    return "@" in email_address


def check_virustotal(url):
    if not VT_API_KEY or VT_API_KEY.startswith("your_"):
        return False
    import base64

    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    api_url = f"https://www.virustotal.com/api/v3/urls/{url_id}"

    try:
        headers = {"x-apikey": VT_API_KEY}
        response = requests.get(api_url, headers=headers, timeout=5)
        if response.status_code == 200:
            stats = response.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            return stats.get("malicious", 0) > 0
    except Exception:
        pass
    return False


def scan_emails():
    global _last_auth_error_at

    email_address, email_password = _read_email_credentials()

    if not email_scanner_configured():
        return

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, email_password)
        mail.select("inbox")

        _, messages = mail.search(None, "UNSEEN")
        for num in messages[0].split():
            _, msg_data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            subject = str(msg.get("Subject"))
            sender = str(msg.get("From"))

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body += str(part.get_payload(decode=True))
            else:
                body = str(msg.get_payload(decode=True))

            links = re.findall(r"(https?://[^\s]+)", body)
            malicious_link_found = any(check_virustotal(link) for link in links)

            ai_result = analyze_email_with_ai(subject, body)
            is_phish = ai_result.get("is_phishing", False)
            ai_reason = ai_result.get("reason", "No reason provided")

            if malicious_link_found or is_phish:
                if malicious_link_found:
                    details = "Malicious link detected by VirusTotal."
                else:
                    details = (
                        f"AI detected phishing ({ai_result.get('confidence')}% confidence): "
                        f"{ai_reason}"
                    )

                analysis = analyze_threat("phishing_email", details)
                full_details = (
                    f"From: {sender}\n"
                    f"Subject: {subject}\n"
                    f"Confidence: {ai_result.get('confidence', 0)}%\n"
                    f"Detection: {details}\n\n"
                    f"AI Recommendations:\n{analysis['ai_suggestion']}"
                )

                log_threat(f"Suspicious Email from {sender}: {details}")
                send_alert("email_threat", "high", full_details)

                try:
                    mail.copy(num, "Quarantine")
                    mail.store(num, "+FLAGS", "\\Deleted")
                    mail.expunge()
                    log_threat(f"Moved email from {sender} to Quarantine.")
                except Exception as e:
                    log_threat(f"Could not move email to Quarantine: {e}")

        mail.close()
        mail.logout()
    except imaplib.IMAP4.error as e:
        err = str(e).upper()
        if "AUTHENTICATIONFAILED" in err or "INVALID CREDENTIALS" in err:
            now = time.time()
            if now - _last_auth_error_at > 300:
                print(
                    "[email_scanner] Gmail login failed. Use a Google **App Password** "
                    "(Google Account → Security → 2-Step Verification → App passwords), "
                    "not your normal Gmail password. Update EMAIL_ADDRESS / EMAIL_PASSWORD "
                    "in client_agent/.env, or leave them empty to disable email scanning."
                )
                _last_auth_error_at = now
        else:
            print(f"[email_scanner] IMAP error: {e}")
    except Exception as e:
        print(f"[email_scanner] Error: {e}")


def run_email_scanner():
    print("Starting AI-Powered Email Scanner...")
    if huggingface_configured():
        print("[email_scanner] Hugging Face LLM enabled (HuggingFaceH4/zephyr-7b-beta) for phishing analysis.")
    else:
        print(
            "[email_scanner] Hugging Face LLM disabled — set HUGGINGFACE_API_KEY in client_agent/.env "
            "to enable AI phishing analysis after rule signals fire."
        )
    while True:
        sync_email_scanner_settings()
        if not email_scanner_configured():
            time.sleep(SCAN_INTERVAL_SECONDS)
            continue
        scan_emails()
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_email_scanner()
