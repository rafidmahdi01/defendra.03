import email
import imaplib
import os
import re
import time

import requests

from scan_config import SCAN_INTERVAL_SECONDS
from utils.config import load_all_configs
from utils.ai_analyzer import analyze_email_with_ai, analyze_threat, huggingface_configured
from utils.alert_sender import log_threat, send_alert
from utils.device_manager import sync_email_scanner_settings

load_all_configs()

VT_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")


def fetch_agent_keys():
    global VT_API_KEY
    backend_url = os.getenv("MARIA_API_URL", os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))
    token = os.getenv("MARIA_API_TOKEN", os.getenv("ENROLLMENT_TOKEN", "agent_token"))
    try:
        res = requests.get(
            f"{backend_url}/api/settings/agent-keys",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        if res.status_code == 200:
            data = res.json()
            VT_API_KEY = data.get("VIRUSTOTAL_API_KEY") or os.getenv("VIRUSTOTAL_API_KEY")
            hf_key = data.get("HUGGINGFACE_API_KEY")
            if hf_key:
                os.environ["HUGGINGFACE_API_KEY"] = hf_key
    except Exception as e:
        print(f"[email_scanner] Could not fetch dynamic agent keys: {e}")


_last_auth_error_at = 0.0
_oauth_access_token: str | None = None
_monitored_email_address: str | None = None


def set_oauth_token(email_address: str, access_token: str) -> None:
    global _oauth_access_token, _monitored_email_address
    _oauth_access_token = access_token
    _monitored_email_address = email_address
    print(f"[email_scanner] OAuth token configured for {email_address}")


def oauth_configured() -> bool:
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
        auth_string = f"user={_monitored_email_address}\1auth=Bearer {_oauth_access_token}\1\1"
        mail.authenticate("XOAUTH2", lambda x: auth_string)
        mail.select("INBOX")

        _, search_data = mail.search(None, "UNSEEN")
        messages = search_data[0].split()

        for num in messages:
            _, msg_data = mail.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject = str(msg.get("Subject", "No Subject"))
            sender = str(msg.get("From", "Unknown Sender"))

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
                    details = f"AI detected phishing ({ai_result.get('confidence')}% confidence): {ai_reason}"

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
    except Exception as e:
        print(f"[email_scanner] Scan error: {e}")


def run_email_scanner():
    print("Starting AI-Powered Email Scanner...")
    fetch_agent_keys()
    if huggingface_configured():
        print("[email_scanner] Hugging Face LLM enabled for phishing analysis.")
    else:
        print("[email_scanner] Hugging Face LLM disabled (no API key configured).")
    
    while True:
        try:
            sync_email_scanner_settings()
            if oauth_configured():
                scan_emails()
        except Exception as e:
            print(f"[email_scanner] Loop error: {e}")
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_email_scanner()
