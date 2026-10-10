import os
import time
import shutil
import hashlib
from pathlib import Path

try:
    import pyclamd
except ImportError:
    pyclamd = None

import win32api
import win32file

from utils.config import get_data_dir, load_all_configs
from utils.alert_sender import send_alert, log_threat
from utils.ai_analyzer import analyze_threat

load_all_configs()

SHOW_POPUPS = False

KNOWN_MALWARE_HASHES = [
    "44d88612fea8a8f36de82e1278abb02f",  # EICAR test file MD5
    "e99a18c428cb38d5f260853678922e03"
]


def get_drives():
    drives = []
    bitmask = win32api.GetLogicalDrives()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drives.append(f"{letter}:\\")
        bitmask >>= 1
    return drives


def get_removable_drives():
    return [drive for drive in get_drives() if win32file.GetDriveType(drive) == win32file.DRIVE_REMOVABLE]


def hash_file(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return None


def scan_usb(drive_path):
    quarantine_dir = get_data_dir() / "quarantine"
    os.makedirs(quarantine_dir, exist_ok=True)
    suspicious_files = []

    try:
        if pyclamd:
            cd = pyclamd.ClamdNetworkSocket()
        else:
            cd = None
    except Exception:
        cd = None

    for root, dirs, files in os.walk(drive_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            filepath = os.path.join(root, file)
            is_malicious = False

            if ext in [".exe", ".bat", ".vbs", ".scr"] or file.lower() == "autorun.inf":
                file_hash = hash_file(filepath)
                if file_hash in KNOWN_MALWARE_HASHES:
                    is_malicious = True

                if cd and not is_malicious:
                    try:
                        scan_result = cd.scan_file(filepath)
                        if scan_result:
                            is_malicious = True
                    except Exception:
                        pass

            if is_malicious:
                suspicious_files.append(filepath)
                try:
                    shutil.move(filepath, str(quarantine_dir / file))
                except Exception as e:
                    print(f"Failed to quarantine {filepath}: {e}")

    if suspicious_files:
        details = f"Malware found on USB {drive_path}. Quarantined {len(suspicious_files)} files."
        log_threat(details)
        analysis = analyze_threat("usb_threat", details)
        full_details = f"{details}\n\nAI Recommendations:\n{analysis['ai_suggestion']}"
        send_alert("usb_threat", "critical", full_details)
    else:
        details = f"USB drive {drive_path} was connected and scanned. No threats found."
        log_threat(details)
        analysis = analyze_threat("usb_inserted", details)
        full_details = f"{details}\n\nAI Recommendations:\n{analysis['ai_suggestion']}"
        send_alert("usb_inserted", "low", full_details)


def run_usb_scanner():
    print("Starting USB Scanner...")
    known_drives = set(get_removable_drives())

    while True:
        try:
            current_drives = set(get_removable_drives())
            new_drives = current_drives - known_drives

            for drive in new_drives:
                print(f"New USB detected: {drive}")
                scan_usb(drive)

            known_drives = current_drives
        except Exception as e:
            print(f"[usb_scanner] Error: {e}")
        time.sleep(2)


if __name__ == "__main__":
    run_usb_scanner()
