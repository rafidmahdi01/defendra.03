from datetime import datetime, timezone

from google.cloud.firestore import Client

from models.models import AlertDoc, AlertSeverity, LogDoc


CRITICAL_KEYWORDS = ("malware", "ransomware", "exfiltration", "privilege escalation", "bruteforce")
MEDIUM_KEYWORDS = ("failed login", "suspicious", "policy violation", "port scan")


def generate_alert_from_log(db: Client, log: LogDoc) -> AlertDoc | None:
    text = f"{log.category} {log.message}".lower()
    severity = None

    if log.severity == "critical" or any(keyword in text for keyword in CRITICAL_KEYWORDS):
        severity = AlertSeverity.critical.value
    elif log.severity in {"warning", "error"} or any(keyword in text for keyword in MEDIUM_KEYWORDS):
        severity = AlertSeverity.medium.value

    if not severity:
        return None

    now = datetime.now(timezone.utc)
    ref = db.collection("alerts").document()
    ref.set(
        {
            "device_id": log.device_id,
            "title": f"{severity.title()} security signal detected",
            "description": log.message,
            "severity": severity,
            "status": "open",
            "rule_name": "log-correlation-v1",
            "created_at": now,
            "acknowledged_at": None,
            "resolved_at": None,
        }
    )
    return AlertDoc.from_firestore(ref.id, ref.get().to_dict())
