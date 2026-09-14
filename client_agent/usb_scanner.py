import os
import time
import shutil
import hashlib
import pyclamd
import win32api
import win32file
from utils.alert_sender import send_alert, log_threat
from utils.ai_analyzer import analyze_threat

# Set to True if you want Windows popups, False for web dashboard only
SHOW_POPUPS = False

KNOWN_MALWARE_HASHES = [
    "44d88612fea8a8f36de82e1278abb02f", # EICAR test file MD5
    "e99a18c428cb38d5f260853678922e03"
]

def get_drives():
    drives = []
    bitmask = win32api.GetLogicalDrives()
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if bitmask & 1:
            drives.append(f"{letter}:\\")
        bitmask >>= 1
    return drives

def get_removable_drives():
    return [drive for drive in get_drives() if win32file.GetDriveType(drive) == win32file.DRIVE_REMOVABLE]

def hash_file(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return None

def show_popup(title, message, is_warning=False):
    if not SHOW_POPUPS:
        return
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    if is_warning:
        messagebox.showwarning(title, message, parent=root)
    else:
        messagebox.showinfo(title, message, parent=root)
    root.destroy()

def scan_usb(drive_path):
    os.makedirs("quarantine", exist_ok=True)
    suspicious_files = []
    
    try:
        cd = pyclamd.ClamdNetworkSocket()
    except pyclamd.ConnectionError:
        cd = None
        print("ClamAV daemon not running. Proceeding with Hash checks only.")

    for root, dirs, files in os.walk(drive_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            filepath = os.path.join(root, file)
            
            is_malicious = False
            
            if ext in ['.exe', '.bat', '.vbs', '.scr'] or file.lower() == 'autorun.inf':
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
                    shutil.move(filepath, os.path.join("quarantine", file))
                except Exception as e:
                    print(f"Failed to quarantine {filepath}: {e}")

    if suspicious_files:
        details = f"Malware found on USB {drive_path}. Quarantined {len(suspicious_files)} files."
        log_threat(details)
        analysis = analyze_threat("usb_threat", details)
        full_details = f"{details}\n\nAI Recommendations:\n{analysis['ai_suggestion']}"
        send_alert("usb_threat", "critical", full_details)
        show_popup("Security Alert", "WARNING: Malicious files found. Access blocked.", is_warning=True)
    else:
        details = f"USB drive {drive_path} was connected and scanned. No threats found."
        log_threat(details)
        analysis = analyze_threat("usb_inserted", details)
        full_details = f"{details}\n\nAI Recommendations:\n{analysis['ai_suggestion']}"
        send_alert("usb_inserted", "low", full_details)
        show_popup("USB Scanner", "USB is safe, you may proceed.")

def run_usb_scanner():
    print("Starting USB Scanner...")
    known_drives = set(get_removable_drives())
    
    while True:
        current_drives = set(get_removable_drives())
        new_drives = current_drives - known_drives
        
        for drive in new_drives:
            print(f"New USB detected: {drive}")
            scan_usb(drive)
            
        known_drives = current_drives
        time.sleep(2)

if __name__ == "__main__":
    run_usb_scanner()