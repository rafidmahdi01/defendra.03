"""
Process and resource behavior monitoring for Defendra.AI Endpoint Agent.
Monitors process execution, high resource usage, and suspicious process activities.
"""

import logging
import time
import psutil
from utils.alert_sender import send_alert, log_threat
from utils.log_sender import send_log

logger = logging.getLogger("client.behavior")

BUILTIN_WHITELIST = {
    "system idle process",
    "system",
    "svchost.exe",
    "explorer.exe",
    "python.exe",
    "pythonw.exe",
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "code.exe",
    "cursor.exe",
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "node.exe",
    "winlogon.exe",
    "lsass.exe",
    "services.exe",
    "csrss.exe",
    "smss.exe",
    "defendraagent.exe",
}

SUSPICIOUS_NAMES = {
    "mimikatz", "pwdump", "fgdump", "wce", "gsecdump",
    "procdump", "netcat", "nc.exe", "nmap", "masscan", "miner", "xmrig"
}


def check_cpu_usage(last_alert_time: float) -> float:
    try:
        cpu = psutil.cpu_percent(interval=1.0)
        if cpu > 85.0:
            now = time.time()
            if now - last_alert_time > 120:  # throttle alert every 2 mins
                msg = f"High CPU usage detected: {cpu:.1f}%"
                logger.warning(msg)
                send_log(category="behavior", severity="warning", message=msg, source="behavior_monitor")
                send_alert("High CPU Usage", "medium", msg)
                return now
    except Exception as e:
        logger.error(f"Error checking CPU usage: {e}")
    return last_alert_time


def check_processes(alerted_pids: set[int]):
    try:
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "exe"]):
            try:
                info = proc.info
                name = (info.get("name") or "").lower()
                pid = info.get("pid")
                if not name or not pid or name in BUILTIN_WHITELIST:
                    continue
                if pid in alerted_pids:
                    continue

                exe = (info.get("exe") or "").lower()

                is_suspicious = (
                    any(s in name for s in SUSPICIOUS_NAMES) or
                    name.endswith(".scr") or
                    name.endswith(".pif")
                )

                if is_suspicious:
                    alerted_pids.add(pid)
                    msg = f"Suspicious process detected: {name} (PID {pid}, Path: {exe or 'Unknown'})"
                    logger.warning(msg)
                    log_threat(msg)
                    send_log(
                        category="behavior",
                        severity="critical",
                        message=msg,
                        source="behavior_monitor",
                        raw_payload={"pid": pid, "name": name, "exe": exe}
                    )
                    send_alert("Suspicious Process Detected", "critical", msg)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Error checking processes: {e}")


def run_behavior_monitor():
    """Entry point for main.py thread."""
    logger.info("Behavior monitor thread started")
    print("[behavior_monitor] Starting real-time behavior monitoring...")
    alerted_pids = set()
    last_cpu_alert = 0.0

    while True:
        try:
            last_cpu_alert = check_cpu_usage(last_cpu_alert)
            check_processes(alerted_pids)
        except Exception as e:
            print(f"[behavior_monitor] Loop error: {e}")
        time.sleep(10)
