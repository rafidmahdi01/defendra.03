"""USB detection and file scanning (hash-based)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from config.settings import get_settings

if TYPE_CHECKING:
    from core.api_client import DefendraClient
    from modules.alert_system import AlertSystem

from modules.usb_hid_guard import HIDGuard

logger = logging.getLogger("client.usb")

# EICAR test string MD5 — safe test pattern, not real malware
KNOWN_BAD_HASHES = {
    "44d88612fea8a8f36de82e1278abb02f",
    "275a021bbfb6489e54d471899f7cc9a5",  # EICAR SHA256 truncated check via md5 of content
}

SUSPICIOUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".vbs", ".js", ".scr", ".ps1", ".dll", ".inf"}

_SCRIPT_EXTENSIONS = {".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".ps1", ".hta", ".wsf"}
_EXEC_EXTENSIONS = {".exe", ".scr", ".com", ".pif", ".dll", ".msi"}
_DECOY_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".jpg", ".jpeg", ".png", ".zip", ".rar", ".mp3", ".mp4"}
_SCRIPT_BAD_TOKENS = (
    b"-encodedcommand", b"-enc ", b"downloadstring", b"downloadfile", b"invoke-expression",
    b"iex(", b"iex ", b"frombase64string", b"certutil -urlcache", b"bitsadmin /transfer",
    b"mshta http", b"wscript.shell", b"-windowstyle hidden", b"-w hidden", b"reg add",
    b"schtasks /create", b"net user ", b"vssadmin delete",
)
_LNK_BAD_TOKENS = (b"cmd.exe", b"powershell", b"wscript", b"cscript", b"mshta", b"rundll32", b"regsvr32")
_MAX_FILES_PER_SCAN = 20000
_FILE_ATTRIBUTE_HIDDEN = 0x2
_FILE_ATTRIBUTE_SYSTEM = 0x4


def _read_head(path: Path, n: int = 262144) -> bytes:
    try:
        with path.open("rb") as fh:
            return fh.read(n)
    except OSError:
        return b""


def _utf16_variants(tokens: tuple[bytes, ...]) -> tuple[bytes, ...]:
    return tokens + tuple(t.decode("latin-1").encode("utf-16le") for t in tokens)


def classify_storage_file(path: Path, at_root: bool) -> tuple[str, str] | None:
    """Return (reason, severity) if the file looks like USB-borne malware, else None."""
    name = path.name.lower()
    ext = path.suffix.lower()

    try:
        attrs = getattr(path.stat(), "st_file_attributes", 0)
    except OSError:
        return None
    hidden = bool(attrs & (_FILE_ATTRIBUTE_HIDDEN | _FILE_ATTRIBUTE_SYSTEM))

    if name == "autorun.inf":
        head = _read_head(path, 8192).lower()
        if any(k in head for k in (b"open=", b"shellexecute=", b"shell\\", b"action=")):
            return "autorun_inf_launcher", "critical"
        return None

    # Decoy double extension: invoice.pdf.exe
    if ext in _EXEC_EXTENSIONS | _SCRIPT_EXTENSIONS and Path(path.stem).suffix.lower() in _DECOY_EXTENSIONS:
        return "double_extension_executable", "high"

    # Classic USB shortcut worm: .lnk on the drive that spawns a shell
    if ext == ".lnk":
        head = _read_head(path, 4096).lower()
        if any(t in head for t in _utf16_variants(_LNK_BAD_TOKENS)):
            return "shortcut_spawns_shell", "high"
        return None

    if ext in _EXEC_EXTENSIONS:
        if hidden:
            return "hidden_executable", "high"
        if at_root and ext != ".dll":
            return "executable_in_drive_root", "medium"
        return None

    if ext in _SCRIPT_EXTENSIONS:
        head = _read_head(path).lower()
        if any(t in head for t in _utf16_variants(_SCRIPT_BAD_TOKENS)):
            return "malicious_script_pattern", "high"
        return None

    # Executable disguised as a document/image
    if ext in _DECOY_EXTENSIONS and _read_head(path, 2) == b"MZ":
        return "executable_disguised_as_document", "high"
    return None


def _hash_file(path: Path, limit_bytes: int = 5_000_000) -> str | None:
    hasher = hashlib.md5()
    try:
        with path.open("rb") as fh:
            remaining = limit_bytes
            while remaining > 0:
                chunk = fh.read(min(65536, remaining))
                if not chunk:
                    break
                hasher.update(chunk)
                remaining -= len(chunk)
        return hasher.hexdigest()
    except OSError:
        return None


def _get_removable_drives_windows() -> list[str]:
    import ctypes

    drives: list[str] = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if bitmask & (1 << i):
            root = f"{letter}:\\"
            dtype = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
            if dtype == 2:  # DRIVE_REMOVABLE
                drives.append(root)
    return drives


def _get_usb_device_info_windows() -> dict[str, str]:
    """Try to detect connected USB input device type on Windows."""
    try:
        completed = subprocess.run(
            ["powershell", "-Command", "Get-PnpDevice -Class Mouse,Keyboard | Select-Object -Property Class,FriendlyName,Manufacturer | ConvertTo-Json"],
            capture_output=True,
            text=True,
            check=True,
        )
        if not completed.stdout:
            return {}
        data = json.loads(completed.stdout)
        if isinstance(data, dict):
            data = [data]
        names = []
        for item in data:
            name = item.get("FriendlyName") or item.get("Manufacturer") or item.get("Class")
            if name:
                names.append(name)
        if names:
            return {"type": "usb_input", "name": ", ".join(sorted(set(names)))}
    except Exception:
        pass
    return {}


def _get_removable_drives_linux() -> list[str]:
    try:
        import pyudev  # type: ignore

        ctx = pyudev.Context()
        drives: list[str] = []
        for device in ctx.list_devices(subsystem="block", DEVTYPE="disk"):
            if device.get("ID_BUS") == "usb":
                for child in device.children:
                    mount = child.get("DEVNAME")
                    if mount:
                        drives.append(mount)
        return drives
    except Exception:
        return []


def _get_connected_usb_devices_windows() -> list[dict[str, str]]:
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-PnpDevice -PresentOnly | Where-Object { $_.Class -in @('Mouse','Keyboard') -or $_.InstanceId -match '^USB' -or $_.FriendlyName -match 'USB' } | Select-Object -Property InstanceId,Class,FriendlyName,Manufacturer | ConvertTo-Json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        if not completed.stdout:
            return []
        data = json.loads(completed.stdout)
        if isinstance(data, dict):
            data = [data]

        devices: list[dict[str, str]] = []
        for item in data:
            device_id = item.get("InstanceId") or item.get("FriendlyName") or item.get("Manufacturer")
            device_class = item.get("Class") or "usb"
            device_name = item.get("FriendlyName") or item.get("Manufacturer") or device_id
            if device_id and device_name:
                devices.append({"id": device_id, "name": device_name, "class": device_class})
        return devices
    except Exception:
        return []


def _get_connected_usb_devices_linux() -> list[dict[str, str]]:
    try:
        import pyudev  # type: ignore

        ctx = pyudev.Context()
        devices: list[dict[str, str]] = []
        for device in ctx.list_devices(subsystem="usb", DEVTYPE="usb_device"):
            name = device.get("ID_MODEL") or device.get("ID_VENDOR") or device.get("DEVNAME")
            device_id = device.sys_name
            devices.append({"id": device_id, "name": name or device_id, "class": device.get("ID_USB_INTERFACES") or "usb"})
        return devices
    except Exception:
        return []


def _get_connected_usb_devices() -> list[dict[str, str]]:
    if sys.platform == "win32":
        return _get_connected_usb_devices_windows()
    if sys.platform.startswith("linux"):
        return _get_connected_usb_devices_linux()
    return []


def list_removable_drives(simulate: bool = False) -> list[str]:
    if sys.platform == "win32":
        return _get_removable_drives_windows()
    if sys.platform.startswith("linux"):
        return _get_removable_drives_linux()
    return []


class USBScanner:
    """Polls for newly connected removable media and scans files."""

    def __init__(self, client: DefendraClient, alerts: AlertSystem) -> None:
        self.client = client
        self.alerts = alerts
        self.settings = get_settings()
        self._stop = threading.Event()
        self._seen: set[str] = set()
        self._seen_usb_devices: set[str] = set()
        self._blocked: set[str] = set()

    def run(self) -> None:
        logger.info("USB scanner started")
        self._seen_usb_devices = {device["id"] for device in _get_connected_usb_devices()}

        # Hardware-level BadUSB/HID watcher runs in its own daemon thread (WMI events).
        self.hid_guard = HIDGuard(self.client, self.alerts)
        hid_guard_active = self.hid_guard.start()

        while not self._stop.is_set():
            if not hid_guard_active:  # legacy polling only when WMI watcher is unavailable
                self._scan_usb_peripherals()

            drives = list_removable_drives(False)
            current = set(drives)

            for drive in current - self._seen:
                self._on_usb_connected(drive)

            self._seen = current
            self._stop.wait(self.settings.usb_poll_interval)

    def _on_usb_connected(self, drive: str) -> None:
        logger.info("USB detected: %s", drive)

        device_info = {}
        if sys.platform == "win32":
            device_info = _get_usb_device_info_windows()

        if device_info:
            msg = f"USB device connected: {drive} ({device_info.get('name')})"
        else:
            msg = f"USB device connected: {drive}"

        self.client.send_log(
            msg,
            category="usb",
            severity="info",
            source="usb_scanner",
            raw_payload=device_info or None,
        )

        if device_info:
            self.alerts.notify(
                "USB Peripheral Connected",
                msg,
                severity="info",
                rule_name="usb_inserted",
                popup=False,
                send_to_server=True,
            )

        threats = self.scan_drive(Path(drive))
        if threats:
            self._blocked.add(drive)
            summary = f"{len(threats)} suspicious file(s) on {drive}"
            self.alerts.notify(
                "USB Threat Detected",
                summary + "\nAccess blocked for this session.",
                severity="critical",
                rule_name="usb_threat",
            )
            for item in threats:
                self.client.send_log(
                    f"Blocked USB file: {item['path']} ({item['reason']})",
                    category="usb",
                    severity="critical",
                    source="usb_scanner",
                    raw_payload=item,
                )
        else:
            self.alerts.notify(
                "USB Scan Complete",
                f"No threats found on {drive}",
                severity="info",
                rule_name="usb_inserted",
                send_to_server=True,
                popup=False,
            )

    def _scan_usb_peripherals(self) -> None:
        current_devices = _get_connected_usb_devices()
        current_ids = {device["id"] for device in current_devices}

        for device in current_devices:
            if device["id"] not in self._seen_usb_devices:
                self._on_usb_peripheral_connected(device)

        self._seen_usb_devices = current_ids

    def _on_usb_peripheral_connected(self, device: dict[str, str]) -> None:
        msg = f"USB peripheral connected: {device['name']} ({device['class']})"
        logger.info(msg)
        self.client.send_log(
            msg,
            category="usb",
            severity="info",
            source="usb_scanner",
            raw_payload=device,
        )
        self.alerts.notify(
            "USB Peripheral Connected",
            msg,
            severity="info",
            rule_name="usb_scanner",
            popup=False,
        )

    def scan_drive(self, root: Path) -> list[dict]:
        """Walk drive and flag suspicious files by extension + hash."""
        if str(root) in self._blocked:
            return [{"path": str(root), "reason": "drive_blocked"}]

        threats: list[dict] = []
        if not root.exists():
            return threats

        scanned = 0
        for dirpath, _, filenames in os.walk(root):
            at_root = Path(dirpath) == root
            for name in filenames:
                scanned += 1
                if scanned > _MAX_FILES_PER_SCAN:
                    logger.warning("Scan cap reached on %s", root)
                    return threats
                path = Path(dirpath) / name
                ext = path.suffix.lower()

                if ext in SUSPICIOUS_EXTENSIONS or name.lower() == "autorun.inf":
                    file_hash = _hash_file(path)
                    if file_hash in KNOWN_BAD_HASHES:
                        self._quarantine(path, "known_bad_hash")
                        threats.append({"path": str(path), "reason": "known_bad_hash", "hash": file_hash})
                        continue
                    try:
                        tiny = ext in SUSPICIOUS_EXTENSIONS and path.stat().st_size < 50
                    except OSError:
                        continue
                    if tiny:
                        self._quarantine(path, "suspicious_executable")
                        threats.append({"path": str(path), "reason": "suspicious_executable", "hash": file_hash})
                        continue

                verdict = classify_storage_file(path, at_root)
                if verdict:
                    reason, sev = verdict
                    # medium = informational (e.g. an exe in the root): report, don't move the user's file
                    if sev != "medium":
                        self._quarantine(path, reason)
                    threats.append({"path": str(path), "reason": reason, "severity": sev,
                                    "hash": _hash_file(path) if path.exists() else None})

        return threats

    def _quarantine(self, path: Path, reason: str) -> None:
        dest_dir = self.settings.quarantine_dir / reason
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{int(time.time() * 1000)}_{path.name}"
        try:
            shutil.move(str(path), str(dest))
            logger.warning("Quarantined %s -> %s", path, dest)
        except OSError as exc:
            logger.error("Quarantine failed for %s: %s", path, exc)

    def stop(self) -> None:
        self._stop.set()
