"""
Sentinel without Hugging Face: intent-specific answers from the Firestore snapshot only.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

_HEADER = (
    "> Snapshot mode — answers are built from your current Firestore data pull. "
    "Add `HUGGINGFACE_API_KEY` to `backend/.env` for AI summaries (https://huggingface.co/settings/tokens).\n\n"
)


def _has_word(text: str, *words: str) -> bool:
    """Whole-word / phrase match to avoid false positives (e.g. 'log' in 'catalog')."""
    t = text.lower()
    for w in words:
        if " " in w:
            if w.lower() in t:
                return True
        elif re.search(rf"\b{re.escape(w.lower())}\b", t):
            return True
    return False


def _slice_body(ctx: str, start: str, ends: tuple[str, ...]) -> str:
    try:
        i = ctx.index(start)
    except ValueError:
        return ""
    rest = ctx[i + len(start) :]
    cut = len(rest)
    for e in ends:
        if not e:
            continue
        j = rest.find(e)
        if j != -1:
            cut = min(cut, j)
    return rest[:cut].strip()


def _device_summary_line(ctx: str) -> str:
    for line in ctx.splitlines():
        if "Devices (sample):" in line:
            return line.strip()
    return ""


def _lines_in_section(ctx: str, start: str, ends: tuple[str, ...]) -> list[str]:
    body = _slice_body(ctx, start, ends)
    if not body:
        return []
    return [ln for ln in body.splitlines() if ln.strip()]


def _build_reply(ctx: str, msg: str) -> str:
    m = msg.lower().strip()
    if not ctx or not ctx.strip() or "No Firestore context" in ctx:
        return (
            _HEADER
            + "No device / alert / log rows were found in this snapshot. "
            "Check Firestore collections `devices`, `alerts`, and `logs`."
        )

    # Order matters: specific topics before generic "threat" / "health".
    if _has_word(m, "usb", "removable drive", "flash drive"):
        return _HEADER + _answer_usb(ctx)

    if _has_word(m, "email", "phish", "phishing", "inbox", "spam", "smtp", "imap", "gmail", "mail", "ceo fraud"):
        return _HEADER + _answer_email_threats(ctx)

    if _has_word(m, "device", "endpoint", "hostname", "host", "fleet", "workstation", "machine", "laptop", "online", "offline"):
        return _HEADER + _answer_devices_only(ctx)

    if _has_word(m, "log", "logs", "event", "events", "activity"):
        return _HEADER + _answer_logs_only(ctx)

    if _has_word(m, "threat", "threats", "alert", "alerts", "incident", "attack", "malware", "ransomware", "ioc"):
        return _HEADER + _answer_alerts_only(ctx)

    if _has_word(m, "health", "status", "overview", "posture", "how are we", "summary"):
        return _HEADER + _answer_health_compact(ctx)

    return _HEADER + _answer_default_menu(ctx)


def _answer_health_compact(ctx: str) -> str:
    summary = _device_summary_line(ctx)
    dev_lines = _lines_in_section(ctx, "Devices (sample):", ("Recent alerts:",))
    alert_lines = _lines_in_section(ctx, "Recent alerts:", ("Recent logs:",))
    log_lines = _lines_in_section(ctx, "Recent logs:", ())
    off = [ln for ln in dev_lines if "offline" in ln.lower()]
    crit_a = sum(1 for ln in alert_lines if "critical" in ln.lower())
    high_a = sum(1 for ln in alert_lines if "high" in ln.lower() and "critical" not in ln.lower())
    parts = ["**Health (snapshot)**\n"]
    if summary:
        parts.append(summary)
    if off:
        parts.append("\n**Offline devices:**\n" + "\n".join(off[:8]))
    parts.append(f"\n**Alert sample:** {len(alert_lines)} rows (critical~{crit_a}, high~{high_a}).")
    if alert_lines:
        parts.append("\n" + "\n".join(alert_lines[:6]))
    parts.append(f"\n**Log sample:** {len(log_lines)} rows (showing up to 5).")
    if log_lines:
        parts.append("\n" + "\n".join(log_lines[:5]))
    return "\n".join(parts)


def _answer_alerts_only(ctx: str) -> str:
    lines = _lines_in_section(ctx, "Recent alerts:", ("Recent logs:",))
    if not lines:
        return "**Alerts**\n\nNo alert rows appear in the latest snapshot (or the `alerts` query returned empty)."
    body = "\n".join(lines)
    return f"**Alerts (from your data)**\n\n{body}"


def _answer_email_threats(ctx: str) -> str:
    kw = ("email", "phish", "phishing", "spam", "smtp", "imap", "inbox", "mail", "ceo", "mime", "message")
    alert_lines = _lines_in_section(ctx, "Recent alerts:", ("Recent logs:",))
    log_lines = _lines_in_section(ctx, "Recent logs:", ())
    a_hits = [ln for ln in alert_lines if any(k in ln.lower() for k in kw)]
    l_hits = [ln for ln in log_lines if any(k in ln.lower() for k in kw) or "email_scan" in ln.lower()]

    parts = ["**Email & phishing-related signals (from snapshot)**\n"]
    if a_hits:
        parts.append("\nFrom **alerts**:\n" + "\n".join(a_hits))
    else:
        parts.append("\nFrom **alerts:** no lines matched email/phishing keywords in this sample.")
    if l_hits:
        parts.append("\nFrom **logs**:\n" + "\n".join(l_hits))
    else:
        parts.append("\nFrom **logs:** no `email_scan` / mail-phish keyword hits in this sample.")
    if not a_hits and not l_hits and (alert_lines or log_lines):
        parts.append(
            "\n\n_Tip: your latest log categories may not include email ingestion yet; "
            "check the Logs page for category `email_scan`._"
        )
    return "\n".join(parts)


def _answer_devices_only(ctx: str) -> str:
    lines = _lines_in_section(ctx, "Devices (sample):", ("Recent alerts:",))
    summary = _device_summary_line(ctx)
    if not lines and not summary:
        return "**Devices**\n\nNo device rows in this snapshot."
    out = "**Devices (from your data)**\n\n"
    if summary:
        out += summary + "\n\n"
    out += "\n".join(lines) if lines else ""
    return out


def _answer_logs_only(ctx: str) -> str:
    lines = _lines_in_section(ctx, "Recent logs:", ())
    if not lines:
        return "**Logs**\n\nNo log rows in this snapshot."
    return "**Recent logs (from your data)**\n\n" + "\n".join(lines)


def _answer_usb(ctx: str) -> str:
    log_lines = _lines_in_section(ctx, "Recent logs:", ())
    hits = [
        ln
        for ln in log_lines
        if _has_word(ln.lower(), "usb", "removable", "flash", "drive letter", "mass storage")
        or "usb" in ln.lower()
    ]
    if hits:
        return "**USB activity (log lines)**\n\n" + "\n".join(hits)
    return (
        "**USB activity**\n\nNo USB-related lines in the latest log sample. "
        "(If you expect USB events, confirm `client_agent` / ingest is writing `usb_scan` logs.)"
    )


def _answer_default_menu(ctx: str) -> str:
    summary = _device_summary_line(ctx)
    return (
        "**Sentinel**\n\n"
        "Try one of these (each returns a different slice of data):\n\n"
        "• `health status` — devices + alert/log counts\n"
        "• `list devices` — endpoints only\n"
        "• `list alerts` or `show threats` — security alerts\n"
        "• `list email threats` — email/phish-related alerts & logs\n"
        "• `show logs` — latest log lines\n"
        "• `usb activity` — USB-related log lines\n\n"
        + (f"**Quick read:** {summary}\n" if summary else "")
    )


def _word_chunks(text: str) -> Iterator[str]:
    for match in re.finditer(r"\S+\s*", text):
        yield match.group(0)


def stream_offline_sentinel(
    system_context: str,
    user_message: str,
    *,
    replace_header: str | None = None,
) -> Iterator[str]:
    reply = _build_reply(system_context, user_message)
    if replace_header is not None and reply.startswith(_HEADER):
        reply = replace_header + reply[len(_HEADER) :]
    yield from _word_chunks(reply)
