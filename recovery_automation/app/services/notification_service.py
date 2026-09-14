"""
Notification system: email, console, Telegram placeholder.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import requests

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("notification_service")


class NotificationService:
    """Dispatch incident and recovery notifications."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def send(
        self,
        *,
        subject: str,
        message: str,
        channels: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send notification on requested channels.
        Default: console + email (if SMTP configured).
        """
        channels = channels or ["console", "email"]
        results: dict[str, Any] = {}

        for channel in channels:
            if channel == "console":
                results["console"] = self._send_console(subject, message)
            elif channel == "email":
                results["email"] = self._send_email(subject, message)
            elif channel == "telegram":
                results["telegram"] = self._send_telegram_placeholder(subject, message)
            else:
                results[channel] = {"status": "skipped", "reason": "unknown channel"}

        logger.info("Notification sent: %s | channels=%s", subject, list(results.keys()))
        return {"subject": subject, "channels": results, "metadata": metadata or {}}

    def _send_console(self, subject: str, message: str) -> dict[str, str]:
        banner = f"\n{'=' * 60}\n[RECOVERY NOTIFICATION] {subject}\n{'-' * 60}\n{message}\n{'=' * 60}\n"
        print(banner)
        return {"status": "delivered"}

    def _send_email(self, subject: str, message: str) -> dict[str, str]:
        if not self.settings.smtp_host or not self.settings.smtp_to:
            logger.info("SMTP not configured; email notification skipped")
            return {"status": "skipped", "reason": "smtp not configured"}

        msg = MIMEMultipart()
        msg["From"] = self.settings.smtp_from
        msg["To"] = self.settings.smtp_to
        msg["Subject"] = f"[Defendra Recovery] {subject}"
        msg.attach(MIMEText(message, "plain"))

        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as server:
                if self.settings.smtp_use_tls:
                    server.starttls()
                if self.settings.smtp_user:
                    server.login(self.settings.smtp_user, self.settings.smtp_password)
                server.sendmail(
                    self.settings.smtp_from,
                    [self.settings.smtp_to],
                    msg.as_string(),
                )
            logger.info("Email sent to %s", self.settings.smtp_to)
            return {"status": "delivered", "to": self.settings.smtp_to}
        except smtplib.SMTPException as exc:
            logger.error("Email delivery failed: %s", exc)
            return {"status": "failed", "error": str(exc)}

    def _send_telegram_placeholder(self, subject: str, message: str) -> dict[str, str]:
        """
        Telegram integration placeholder.
        Set TELEGRAM_ENABLED=true and provide bot token + chat id to enable.
        """
        if not self.settings.telegram_enabled:
            logger.info("[TELEGRAM PLACEHOLDER] Disabled — would send: %s", subject)
            return {"status": "placeholder", "reason": "telegram disabled"}

        token = self.settings.telegram_bot_token
        chat_id = self.settings.telegram_chat_id
        if not token or not chat_id:
            return {"status": "skipped", "reason": "missing token or chat_id"}

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(
                url,
                json={"chat_id": chat_id, "text": f"*{subject}*\n{message}", "parse_mode": "Markdown"},
                timeout=10,
            )
            if resp.status_code == 200:
                return {"status": "delivered"}
            return {"status": "failed", "http": resp.status_code}
        except requests.RequestException as exc:
            logger.error("Telegram send failed: %s", exc)
            return {"status": "failed", "error": str(exc)}
