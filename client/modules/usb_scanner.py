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

logger = logging.getLogger("client.usb")

# EICAR test string MD5 — safe test pattern, not real malware
KNOWN_BAD_HASHES = {
    "44d88612fea8a8f36de82e1278abb02f",
    "275a021bbfb6489e54d471899f7cc9a5",  # EICAR SHA256 truncated check via md5 of content
}

SUSPICIOUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".vbs", ".js", ".scr", ".ps1", ".dll", ".inf"}


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

        while not self._stop.is_set():
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

        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                path = Path(dirpath) / name
                ext = path.suffix.lower()
                if ext not in SUSPICIOUS_EXTENSIONS and name.lower() != "autorun.inf":
                    continue

                file_hash = _hash_file(path)
                if file_hash in KNOWN_BAD_HASHES:
                    self._quarantine(path, "known_bad_hash")
                    threats.append({"path": str(path), "reason": "known_bad_hash", "hash": file_hash})
                    continue

                if ext in SUSPICIOUS_EXTENSIONS and path.stat().st_size < 50:
                    self._quarantine(path, "suspicious_executable")
                    threats.append(
                        {"path": str(path), "reason": "suspicious_executable", "hash": file_hash}
                    )

        return threats

    def _quarantine(self, path: Path, reason: str) -> None:
        dest_dir = self.settings.quarantine_dir / reason
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        try:
            shutil.move(str(path), str(dest))
            logger.warning("Quarantined %s -> %s", path, dest)
        except OSError as exc:
            logger.error("Quarantine failed for %s: %s", path, exc)

    def stop(self) -> None:
        self._stop.set()
