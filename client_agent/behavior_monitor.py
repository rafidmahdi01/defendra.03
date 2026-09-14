import time
import psutil
import os
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from scan_config import SCAN_INTERVAL_SECONDS
from utils.alert_sender import send_alert, log_threat, MARIA_API_URL, _get_or_refresh_token
from utils.ai_analyzer import analyze_threat
import requests

# Set to True if you want Windows popups, False for web dashboard only
SHOW_POPUPS = False

# Built-in whitelist — always safe, never sent to the kill list
_BUILTIN_WHITELIST = {name.lower() for name in [
    "explorer.exe", "svchost.exe", "system idle process", "system",
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", "vivaldi.exe",
    "python.exe", "pythonw.exe",
    "cmd.exe", "powershell.exe", "pwsh.exe",
    "code.exe", "cursor.exe",
    "discord.exe", "electron.exe",
    "node.exe", "npm.exe", "node_modules",
    "taskmgr.exe", "notepad.exe", "winlogon.exe", "lsass.exe",
    "services.exe", "smss.exe", "csrss.exe", "wininit.exe",
]}

# Dynamic whitelist fetched from the backend (refreshed every 5 minutes)
_remote_whitelist: set[str] = set()
_remote_whitelist_fetched_at: float = 0
_REMOTE_WHITELIST_TTL = 300  # seconds


def _fetch_remote_whitelist() -> set[str]:
    """Pull the custom whitelist from the backend API."""
    try:
        token = _get_or_refresh_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = requests.get(f"{MARIA_API_URL}/api/whitelist", headers=headers, timeout=5)
        if resp.status_code == 200:
            return {entry["process"].lower() for entry in resp.json()}
    except Exception as e:
        print(f"[behavior_monitor] Could not fetch remote whitelist: {e}")
    return set()


def _get_whitelist() -> set[str]:
    """Return the merged built-in + remote whitelist, refreshing remote every 5 min."""
    global _remote_whitelist, _remote_whitelist_fetched_at
    now = time.time()
    if now - _remote_whitelist_fetched_at > _REMOTE_WHITELIST_TTL:
        _remote_whitelist = _fetch_remote_whitelist()
        _remote_whitelist_fetched_at = now
        if _remote_whitelist:
            print(f"[behavior_monitor] Remote whitelist loaded: {len(_remote_whitelist)} entries")
    return _BUILTIN_WHITELIST | _remote_whitelist


# Keep WHITELIST as a convenience alias pointing at the built-in set
WHITELIST = _BUILTIN_WHITELIST
TEMP_DIRS = [os.environ.get("TEMP", "C:\\Temp").lower(), os.environ.get("APPDATA", "C:\\").lower()]

file_mod_timestamps = deque()
_last_ransomware_alert = 0  # cooldown tracker

class RansomwareDetector(FileSystemEventHandler):
    def on_modified(self, event):
        self._record_event()
        
    def on_moved(self, event):
        self._record_event()
        
    def _record_event(self):
        global _last_ransomware_alert
        now = time.time()
        file_mod_timestamps.append(now)
        while file_mod_timestamps and file_mod_timestamps[0] < now - 60:
            file_mod_timestamps.popleft()

        # Only alert if >200 files in 60s AND no alert in last 5 minutes
        if len(file_mod_timestamps) > 200 and (now - _last_ransomware_alert) > 300:
            details = "Ransomware pattern detected: >200 files modified/renamed within 60s"
            log_threat(details)
            analysis = analyze_threat("behavior_threat", details)
            full_details = f"{details}\n\nAI Recommendations:\n{analysis['ai_suggestion']}"
            send_alert("behavior_threat", "critical", full_details)
            _last_ransomware_alert = now
            if SHOW_POPUPS:
                show_popup("WARNING: Suspicious process detected. IT admin has been notified.")
            file_mod_timestamps.clear()

def show_popup(message):
    if not SHOW_POPUPS:
        return
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showwarning("Security Alert", message, parent=root)
    root.destroy()

def monitor_processes():
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent']):
        try:
            info = proc.info
            name = info['name']
            exe = info['exe']
            cpu = info['cpu_percent']
            
            is_suspicious = False
            reason = ""

            if name and name.lower() not in _get_whitelist():
                if cpu and cpu > 70.0:
                    is_suspicious = True
                    reason = f"High CPU usage ({cpu}%)"
                if exe:
                    exe_lower = exe.lower()
                    if any(temp_dir in exe_lower for temp_dir in TEMP_DIRS):
                        is_suspicious = True
                        reason = f"Running from Temp/AppData directory"

            if is_suspicious:
                details = f"Suspicious process '{name}' (PID: {info['pid']}): {reason}"
                log_threat(details)
                analysis = analyze_threat("behavior_threat", details)
                full_details = f"{details}\n\nAI Recommendations:\n{analysis['ai_suggestion']}"
                send_alert("behavior_threat", "high", full_details)
                if SHOW_POPUPS:
                    show_popup("WARNING: Suspicious process detected. IT admin has been notified.")
                try:
                    proc.kill()
                    log_threat(f"Successfully killed process {name}")
                except psutil.AccessDenied:
                    log_threat(f"Failed to kill process {name}: Access Denied")
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def run_behavior_monitor():
    print("Starting Behavior Monitor...")
    path_to_watch = os.path.expanduser("~")
    event_handler = RansomwareDetector()
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=True)
    observer.start()
    
    try:
        while True:
            monitor_processes()
            time.sleep(SCAN_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    run_behavior_monitor()