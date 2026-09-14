"""Pre-click email scanning via keyword / fake-domain heuristics."""

from __future__ import annotations

import logging
import re
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from config.settings import get_settings

if TYPE_CHECKING:
    from core.api_client import DefendraClient
    from modules.alert_system import AlertSystem

logger = logging.getLogger("client.email")

SUSPICIOUS_KEYWORDS = [
    "urgent action required",
    "verify your account",
    "password expired",
    "wire transfer",
    "bitcoin",
    "click here immediately",
    "suspended account",
    "invoice attached",
    "payroll update",
    "confidential document",
]

FAKE_DOMAIN_PATTERNS = [
    r"gooogle\.",
    r"paypa1\.",
    r"microsft\.",
    r"amaz0n\.",
    r"apple-id\.",
    r"secure-login-",
    r"\.tk$",
    r"\.ml$",
]

TRUSTED_DOMAINS = {
    "google.com",
    "microsoft.com",
    "github.com",
    "apple.com",
    "amazon.com",
}


def _extract_links(text: str) -> list[str]:
    return re.findall(r"https?://[^\s<>\"']+", text, flags=re.IGNORECASE)


def _domain_looks_fake(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return True
    if not host:
        return True
    if host in TRUSTED_DOMAINS or any(host.endswith("." + d) for d in TRUSTED_DOMAINS):
        return False
    return any(re.search(pat, host) for pat in FAKE_DOMAIN_PATTERNS)


def scan_email_content(subject: str, body: str, sender: str = "") -> dict:
    """Return scan verdict with matched signals."""
    text = f"{subject}\n{body}".lower()
    keyword_hits = [kw for kw in SUSPICIOUS_KEYWORDS if kw in text]
    links = _extract_links(body)
    bad_links = [link for link in links if _domain_looks_fake(link)]

    sender_lower = sender.lower()
    sender_suspicious = bool(re.search(r"support\d+@|no-reply-[a-z0-9]{6,}@", sender_lower))

    score = len(keyword_hits) + len(bad_links) * 2 + (1 if sender_suspicious else 0)
    is_phishing = score >= 2

    return {
        "is_phishing": is_phishing,
        "score": score,
        "keyword_hits": keyword_hits,
        "bad_links": bad_links,
        "sender_suspicious": sender_suspicious,
    }


class EmailScanner:
    """
    Scans live email evidence files dropped into the inbox folder.
    """

    def __init__(self, client: DefendraClient, alerts: AlertSystem) -> None:
        self.client = client
        self.alerts = alerts
        self.settings = get_settings()
        self._stop = threading.Event()
        self._processed: set[str] = set()
        self.inbox = self.settings.data_dir / "inbox"

    def run(self) -> None:
        logger.info("Email scanner started (inbox=%s)", self.inbox)
        self.inbox.mkdir(parents=True, exist_ok=True)

        while not self._stop.is_set():
            for eml in self.inbox.glob("*.eml"):
                key = f"{eml.name}:{eml.stat().st_mtime_ns}"
                if key in self._processed:
                    continue
                try:
                    self._scan_file(eml)
                except OSError as exc:
                    logger.error("Failed to scan %s: %s", eml.name, exc)
                self._processed.add(key)
            self._stop.wait(self.settings.email_scan_interval)

    def _scan_file(self, path: Path) -> None:
        raw = path.read_text(encoding="utf-8", errors="replace")
        subject = ""
        sender = ""
        body_lines: list[str] = []
        in_body = False

        for line in raw.splitlines():
            if not in_body:
                if line.lower().startswith("subject:"):
                    subject = line.split(":", 1)[1].strip()
                elif line.lower().startswith("from:"):
                    sender = line.split(":", 1)[1].strip()
                elif line.strip() == "":
                    in_body = True
            else:
                body_lines.append(line)

        body = "\n".join(body_lines)
        result = scan_email_content(subject, body, sender)

        self.client.send_log(
            f"Email scanned: {path.name} score={result['score']}",
            category="email",
            severity="critical" if result["is_phishing"] else "info",
            source="email_scanner",
            raw_payload={"file": path.name, **result},
        )

        if result["is_phishing"]:
            self.alerts.notify(
                "Suspicious Email Blocked",
                f"{path.name}\nSubject: {subject}\nScore: {result['score']}",
                severity="critical",
                rule_name="email_scanner",
            )
            self._move_to_blocked(path)
        else:
            logger.info("Email OK: %s", path.name)

    def _move_to_blocked(self, path: Path) -> None:
        """Move scanned email to blocked/ — safe on Windows if dest already exists."""
        import shutil

        if not path.exists():
            return

        blocked_dir = self.inbox / "blocked"
        blocked_dir.mkdir(parents=True, exist_ok=True)
        dest = blocked_dir / path.name

        if dest.exists():
            path.unlink(missing_ok=True)
            logger.info("Email already blocked: %s", path.name)
            return

        try:
            path.replace(dest)
        except OSError:
            shutil.move(str(path), str(dest))
        logger.info("Moved blocked email to %s", dest)

    def stop(self) -> None:
        self._stop.set()
