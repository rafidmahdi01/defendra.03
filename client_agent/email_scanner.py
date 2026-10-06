import email
import imaplib
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from scan_config import SCAN_INTERVAL_SECONDS
from utils.ai_analyzer import analyze_email_with_ai, analyze_threat, huggingface_configured
from utils.alert_sender import log_threat, send_alert
from utils.device_manager import sync_email_scanner_settings

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=_BASE_DIR / ".env")
VT_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

_last_auth_error_at = 0.0

# Global variable to hold OAuth 2.0 access token (passed in-memory from backend)
_oauth_access_token: str | None = None
_monitored_email_address: str | None = None


# Removed legacy functions:
# - _read_email_credentials: no longer reading plaintext passwords from .env
# - email_scanner_configured: replaced by token-based authentication check


def set_oauth_token(email_address: str, access_token: str) -> None:
    """
    Set OAuth 2.0 credentials for IMAP authentication.
    Called by the backend after completing OAuth flow.
    """
    global _oauth_access_token, _monitored_email_address
    _oauth_access_token = access_token
    _monitored_email_address = email_address
    print(f"[email_scanner] OAuth token configured for {email_address}")


def oauth_configured() -> bool:
    """Returns True if OAuth 2.0 credentials are available in memory."""
    return bool(_oauth_access_token and _monitored_email_address)


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

    if not oauth_configured():
        return

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        
        # Use XOAUTH2 SASL mechanism instead of password authentication
        auth_string = f"user={_monitored_email_address}\1auth=Bearer {_oauth_access_token}\1\1"
        mail.authenticate("XOAUTH2", lambda x: auth_string.encode())
        
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
                    "[email_scanner] Gmail OAuth authentication failed. "
                    "The OAuth 2.0 access token may have expired. "
                    "Please re-authenticate through the Defendra dashboard."
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
    print("[email_scanner] Waiting for OAuth 2.0 token from dashboard...")
    while True:
        sync_email_scanner_settings()
        if not oauth_configured():
            time.sleep(SCAN_INTERVAL_SECONDS)
            continue
        scan_emails()
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_email_scanner()
