"""
Full system scan — runs once on startup, then every 6 hours.
Scans: running processes, startup items, open ports, suspicious files.
Sends all findings to HuggingFace for AI analysis and reports to the dashboard.
"""

import os
import socket
import platform
import subprocess
import psutil
from datetime import datetime, timezone
from utils.alert_sender import send_alert, log_threat
from utils.log_sender import send_log
from utils.ai_analyzer import analyze_threat

# Files/folders to skip during scan
SKIP_DIRS = {
    "windows", "program files", "program files (x86)",
    "system32", "syswow64", "$recycle.bin", "node_modules",
}

SUSPICIOUS_EXTENSIONS = {".exe", ".bat", ".vbs", ".ps1", ".scr", ".com", ".pif"}

SUSPICIOUS_PROCESS_NAMES = {
    "mimikatz", "pwdump", "fgdump", "wce", "gsecdump",
    "procdump", "netcat", "nc.exe", "nmap", "masscan",
}

SUSPICIOUS_PORTS = {4444, 1337, 31337, 9001, 9050}  # common RAT/C2 ports


def scan_processes() -> list[dict]:
    """Scan all running processes for suspicious activity."""
    findings = []
    for proc in psutil.process_iter(["pid", "name", "exe", "username"]):
        try:
            name = (proc.info["name"] or "").lower()
            exe = (proc.info["exe"] or "").lower()

            if any(s in name for s in SUSPICIOUS_PROCESS_NAMES):
                findings.append({
                    "type": "suspicious_process",
                    "severity": "critical",
                    "detail": f"Known malicious process detected: {proc.info['name']} (PID {proc.info['pid']})",
                })
            elif exe and any(d in exe for d in ["\\temp\\", "\\appdata\\local\\temp\\"]):
                if any(exe.endswith(ext) for ext in SUSPICIOUS_EXTENSIONS):
                    findings.append({
                        "type": "suspicious_process",
                        "severity": "high",
                        "detail": f"Process running from temp: {proc.info['name']} at {exe}",
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return findings


def scan_open_ports() -> list[dict]:
    """Check for suspicious open network ports."""
    findings = []
    try:
        connections = psutil.net_connections(kind="inet")
        for conn in connections:
            if conn.laddr and conn.laddr.port in SUSPICIOUS_PORTS and conn.status == "LISTEN":
                findings.append({
                    "type": "suspicious_port",
                    "severity": "high",
                    "detail": f"Suspicious port open: {conn.laddr.port} (commonly used by RATs/C2 servers)",
                })
    except Exception:
        pass
    return findings


def scan_startup_items() -> list[dict]:
    """Check Windows registry startup items for suspicious entries."""
    findings = []
    if platform.system() != "Windows":
        return findings
    try:
        result = subprocess.run(
            ["reg", "query", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("HKEY"):
                continue
            line_lower = line.lower()
            if any(ext in line_lower for ext in [".vbs", ".ps1", ".bat", "\\temp\\"]):
                findings.append({
                    "type": "suspicious_startup",
                    "severity": "high",
                    "detail": f"Suspicious startup entry: {line[:200]}",
                })
    except Exception:
        pass
    return findings


def scan_temp_files() -> list[dict]:
    """Scan temp directories for recently created suspicious executable files (last 24h)."""
    import time
    findings = []
    cutoff = time.time() - 86400  # only files created in the last 24 hours
    temp_dirs = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
    ]
    seen_files = set()
    for temp_dir in temp_dirs:
        if not temp_dir or not os.path.isdir(temp_dir):
            continue
        try:
            for fname in os.listdir(temp_dir):
                if fname in seen_files:
                    continue
                seen_files.add(fname)
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SUSPICIOUS_EXTENSIONS:
                    continue
                fpath = os.path.join(temp_dir, fname)
                try:
                    if os.path.getctime(fpath) > cutoff:
                        findings.append({
                            "type": "suspicious_file",
                            "severity": "medium",
                            "detail": f"Recently created executable in temp folder: {fpath}",
                        })
                except Exception:
                    pass
        except Exception:
            pass
    return findings


def get_system_info() -> str:
    """Gather basic system information for context."""
    try:
        hostname = socket.gethostname()
        os_info = f"{platform.system()} {platform.release()}"
        cpu_count = psutil.cpu_count()
        ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        disk = psutil.disk_usage("/")
        disk_free_gb = round(disk.free / (1024 ** 3), 1)
        return (
            f"Host: {hostname} | OS: {os_info} | "
            f"CPU cores: {cpu_count} | RAM: {ram_gb}GB | "
            f"Disk free: {disk_free_gb}GB"
        )
    except Exception:
        return "System info unavailable"


def run_full_scan():
    """Run a full system scan and report all findings."""
    print(f"[system_scanner] Starting full system scan at {datetime.now(timezone.utc).isoformat()}")

    system_info = get_system_info()
    send_log("system_scan", "info", f"Full system scan started. {system_info}", source="system_scanner")

    all_findings = (
        scan_processes() +
        scan_open_ports() +
        scan_startup_items() +
        scan_temp_files()
    )

    if not all_findings:
        send_log("system_scan", "info", "Full system scan completed. No threats found.", source="system_scanner")
        print("[system_scanner] Scan complete — system clean.")
        return

    print(f"[system_scanner] Found {len(all_findings)} issue(s). Analyzing...")

    # Group findings by severity and send alerts
    for finding in all_findings:
        detail = finding["detail"]
        threat_type = finding["type"]
        severity = finding["severity"]

        log_threat(detail)

        # Get AI analysis + recommendations
        analysis = analyze_threat(threat_type, detail)
        full_description = f"{detail}\n\nAI Recommendations:\n{analysis['ai_suggestion']}"

        send_alert(threat_type, severity, full_description)
        send_log("system_scan", severity, detail, source="system_scanner")

    summary = f"System scan complete. Found {len(all_findings)} issue(s) across processes, ports, startup items, and temp files."
    send_log("system_scan", "warning", summary, source="system_scanner")
    print(f"[system_scanner] {summary}")


def run_system_scanner(interval_hours: int = 6):
    """Run full scan on startup then repeat every interval_hours."""
    import time
    while True:
        run_full_scan()
        time.sleep(interval_hours * 3600)
