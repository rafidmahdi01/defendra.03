import os
import re
from dotenv import load_dotenv

load_dotenv()

HUGGINGFACE_API_KEY = (os.getenv("HUGGINGFACE_API_KEY") or "").strip()
HUGGINGFACE_MODEL = "HuggingFaceH4/zephyr-7b-beta"

_PLACEHOLDER_HF_KEYS = {
    "",
    "your_huggingface_api_key_here",
    "your_hf_api_key_here",
    "change-me",
}


def huggingface_configured() -> bool:
    """True when a real Hugging Face token is set (not a template placeholder)."""
    if HUGGINGFACE_API_KEY in _PLACEHOLDER_HF_KEYS:
        return False
    if HUGGINGFACE_API_KEY.startswith("your_"):
        return False
    return len(HUGGINGFACE_API_KEY) >= 10

# ── Rule-based phishing keywords ─────────────────────────────────────────────

PHISHING_KEYWORDS = [
    "verify your account", "confirm your password", "click here to login",
    "your account has been suspended", "unusual sign-in activity",
    "update your payment", "banking details", "reset your password immediately",
    "you have won", "claim your prize", "urgent action required",
    "your account will be closed", "validate your credentials",
    "enter your social security", "provide your credit card",
    "limited time offer", "act now", "wire transfer",
    "nigerian prince", "inheritance funds", "lottery winner",
]

PHISHING_PATTERNS = [
    r"http[s]?://(?!.*\.(gov|edu))[^\s]+\.(xyz|tk|ml|ga|cf|gq|top|click|link)",
    r"dear (customer|user|member|client)",
    r"(verify|confirm|validate).{0,30}(account|identity|email|password)",
    r"(suspend|terminat|clos).{0,20}account",
]

# ── Rule-based threat suggestions (instant fallback) ─────────────────────────

THREAT_SUGGESTIONS = {
    "usb_threat": [
        "Immediately remove the USB drive from the device.",
        "Run a full antivirus scan on the affected device.",
        "Check quarantine folder for the malicious files.",
        "Notify your IT administrator about the incident.",
        "Do not plug the USB into any other device.",
    ],
    "usb_inserted": [
        "USB drive connected and scanned — no threats found.",
        "Monitor device activity for any unusual behaviour.",
        "Ensure the USB is from a trusted source before using files.",
    ],
    "behavior_threat": [
        "Investigate the flagged process immediately.",
        "Isolate the device from the network if ransomware is suspected.",
        "Check recently modified files for encryption patterns.",
        "Run a full malware scan on the device.",
        "Restore files from backup if data has been encrypted.",
        "Report the incident to your IT security team.",
    ],
    "phishing_email": [
        "Do not click any links or download attachments in the email.",
        "Report the email to your IT administrator.",
        "Delete the email from your inbox immediately.",
        "Change your password if you accidentally clicked a link.",
        "Enable multi-factor authentication on your accounts.",
    ],
    "default": [
        "Investigate the threat source immediately.",
        "Isolate affected systems if necessary.",
        "Review recent logs for unusual activity.",
        "Contact your IT security team.",
        "Document the incident for compliance reporting.",
    ],
}


# ── AI-powered analysis via Hugging Face ─────────────────────────────────────

def _call_huggingface(prompt: str) -> str | None:
    """Call HuggingFace inference API and return text or None on failure."""
    if not huggingface_configured():
        return None
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(token=HUGGINGFACE_API_KEY)
        response = client.chat.completions.create(
            model=HUGGINGFACE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Silently fall back to rule-based analysis
        return None


def analyze_threat(threat_type: str, details: str) -> dict:
    """
    Analyze a detected threat and return AI suggestions.
    Falls back to rule-based suggestions if API is unavailable.
    """
    fallback_suggestions = THREAT_SUGGESTIONS.get(threat_type, THREAT_SUGGESTIONS["default"])

    prompt = f"""You are a cybersecurity expert assistant for Defendra, a cyber resilience platform.

A security threat has been detected on an endpoint device:

Threat Type: {threat_type}
Details: {details}

Provide a clear, concise response with:
1. A brief explanation of what this threat means (1-2 sentences)
2. Exactly 3-5 specific, actionable steps the user should take right now

Keep it short and direct. No markdown headers."""

    ai_response = _call_huggingface(prompt)

    if ai_response:
        return {
            "threat_type": threat_type,
            "details": details,
            "ai_suggestion": ai_response,
            "source": "ai",
        }
    else:
        return {
            "threat_type": threat_type,
            "details": details,
            "ai_suggestion": "\n".join(f"• {s}" for s in fallback_suggestions),
            "source": "rules",
        }


def analyze_email_with_ai(subject: str, body: str) -> dict:
    """
    Analyze email for phishing using rules first, then AI if available.
    """
    text = f"{subject} {body}".lower()
    matched_keywords = [kw for kw in PHISHING_KEYWORDS if kw in text]
    matched_patterns = [p for p in PHISHING_PATTERNS if re.search(p, text, re.IGNORECASE)]
    total_signals = len(matched_keywords) + len(matched_patterns)

    # Use AI for deeper analysis if we have signals
    if total_signals > 0 and huggingface_configured():
        prompt = f"""You are a cybersecurity expert. Analyze this email for phishing.

Subject: {subject}
Body: {body[:500]}

Respond ONLY with valid JSON (no markdown):
{{"is_phishing": true/false, "confidence": 0-100, "reason": "one sentence explanation"}}"""

        ai_text = _call_huggingface(prompt)
        if ai_text:
            try:
                import json
                clean = re.sub(r"```[a-z]*", "", ai_text).strip().rstrip("`").strip()
                parsed = json.loads(clean)
            except Exception:
                parsed = None
            if parsed:
                return parsed

    # Rule-based fallback
    if total_signals >= 3:
        confidence = min(95, 60 + total_signals * 5)
        reason = f"Matched {total_signals} phishing signals: {', '.join(matched_keywords[:3])}"
        return {"is_phishing": True, "confidence": confidence, "reason": reason, "source": "rules"}
    elif total_signals >= 1:
        return {
            "is_phishing": False,
            "confidence": total_signals * 20,
            "reason": f"Possible phishing — matched: {', '.join(matched_keywords[:2])}",
            "source": "rules",
        }
    else:
        return {"is_phishing": False, "confidence": 5, "reason": "No phishing signals detected", "source": "rules"}
