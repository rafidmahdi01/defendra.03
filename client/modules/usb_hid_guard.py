"""BadUSB / Rubber Ducky detection via raw WMI hardware events (Windows).

Listens for ``__InstanceCreationEvent`` on ``Win32_PnPEntity`` so a device is seen
the moment Windows enumerates it, not when a volume mounts. New USB keyboards and
mice are compared against an allowlist baseline; unknown ones raise an alert.

Runs in its own daemon thread (COM is initialised per thread), so it never blocks
the pywebview / GUI loop.
"""

from __future__ import annotations

import json
import logging
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from config.settings import get_settings

if TYPE_CHECKING:
    from core.api_client import DefendraClient
    from modules.alert_system import AlertSystem

logger = logging.getLogger("client.usb.hid")

_VIDPID_RE = re.compile(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", re.IGNORECASE)
_SERIAL_RE = re.compile(r"^(?:USB|HID)\\VID_[0-9A-F]{4}&PID_[0-9A-F]{4}(?:&MI_[0-9A-F]{2})?\\([^\\]+)$", re.IGNORECASE)

# Seconds to wait after the last event for a device before judging it, so that all
# of its interfaces (keyboard + storage + serial ...) are collected first.
_SETTLE_SECONDS = 3.0

# Maker/dev-board vendors. A hint only (raises risk), never proof: many legit parts use these.
_MAKER_VIDS = {
    "16d0": "Digistump (Digispark)",
    "16c0": "V-USB / Teensy shared VID",
    "2341": "Arduino",
    "1b4f": "SparkFun (Pro Micro)",
    "239a": "Adafruit",
    "2e8a": "Raspberry Pi (RP2040 boards)",
}

_WQL = (
    "SELECT * FROM __InstanceCreationEvent WITHIN 1 "
    "WHERE TargetInstance ISA 'Win32_PnPEntity' "
    "AND (TargetInstance.DeviceID LIKE 'USB%' OR TargetInstance.DeviceID LIKE 'HID%')"
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [str(value)]


def parse_vid_pid(device_id: str, hardware_ids: list[str] | None = None) -> tuple[str, str] | None:
    for text in [device_id, *(hardware_ids or [])]:
        m = _VIDPID_RE.search(text or "")
        if m:
            return m.group(1).lower(), m.group(2).lower()
    return None


def classify_node(device_id: str, name: str, pnp_class: str, service: str, ids: list[str]) -> str:
    """Return keyboard | mouse | hid | storage | other for a single PnP node."""
    blob = " ".join([device_id, *ids]).upper()
    lname = (name or "").lower()
    svc = (service or "").lower()
    cls = (pnp_class or "").lower()

    if device_id.upper().startswith("USBSTOR") or cls == "diskdrive" or svc in ("usbstor", "uaspstor"):
        return "storage"
    if cls == "keyboard" or svc == "kbdhid" or "CLASS_03&SUBCLASS_01&PROT_01" in blob or "keyboard" in lname:
        return "keyboard"
    if cls == "mouse" or svc == "mouhid" or "CLASS_03&SUBCLASS_01&PROT_02" in blob or "mouse" in lname:
        return "mouse"
    if cls == "hidclass" or "CLASS_03" in blob or device_id.upper().startswith("HID\\"):
        return "hid"
    return "other"


class HIDGuard:
    """WMI-driven USB device watcher with HID allowlist baseline."""

    def __init__(self, client: DefendraClient, alerts: AlertSystem) -> None:
        self.client = client
        self.alerts = alerts
        self.settings = get_settings()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        # (vid, pid) -> {"first": ts, "last": ts, "nodes": [node dict]}
        self._pending: dict[tuple[str, str], dict[str, Any]] = {}
        # Recent storage events with no VID/PID (USBSTOR ids carry none): list of timestamps
        self._recent_storage: list[float] = []
        self._allowlist: dict[str, dict[str, Any]] = {}
        self._disabled: dict[str, list[str]] = {}  # "vid:pid" -> disabled instance ids
        self._load_allowlist()

    # ── lifecycle ──────────────────────────────────────────────────────────
    @staticmethod
    def available() -> bool:
        if sys.platform != "win32":
            return False
        try:
            import pythoncom  # noqa: F401
            import wmi  # noqa: F401
            return True
        except ImportError:
            logger.warning("wmi / pywin32 not installed — HID guard disabled (pip install wmi pywin32)")
            return False

    def start(self) -> bool:
        if not self.available():
            return False
        self._thread = threading.Thread(target=self._run, daemon=True, name="usb-hid-guard")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    # ── allowlist ──────────────────────────────────────────────────────────
    @property
    def _allowlist_path(self):
        return self.settings.data_dir / "usb_hid_allowlist.json"

    def _load_allowlist(self) -> None:
        try:
            data = json.loads(self._allowlist_path.read_text(encoding="utf-8"))
            self._allowlist = data.get("devices", {})
        except FileNotFoundError:
            self._allowlist = {}
        except (OSError, ValueError) as exc:
            logger.error("Could not read HID allowlist (%s) — treating as empty", exc)
            self._allowlist = {}

    def _save_allowlist(self) -> None:
        try:
            tmp = self._allowlist_path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"devices": self._allowlist}, indent=2), encoding="utf-8")
            tmp.replace(self._allowlist_path)
        except OSError as exc:
            logger.error("Could not save HID allowlist: %s", exc)

    def is_trusted(self, vid: str, pid: str) -> bool:
        return f"{vid}:{pid}" in self._allowlist

    def trust_device(self, vid: str, pid: str, description: str = "", note: str = "user_approved") -> None:
        """Add a device to the allowlist (call from the GUI after the user approves) and re-enable it."""
        key = f"{vid.lower()}:{pid.lower()}"
        with self._lock:
            self._allowlist[key] = {"description": description, "added": _utcnow(), "note": note}
            self._save_allowlist()
            ids = self._disabled.pop(key, [])
        for instance_id in ids:
            self._pnputil("enable-device", instance_id)

    def _learn_baseline_if_first_run(self, c: Any) -> None:
        """First ever run: trust every USB keyboard/mouse already plugged in."""
        if self._allowlist_path.exists():
            return
        count = 0
        try:
            for ent in c.Win32_PnPEntity(["DeviceID", "Name", "PNPClass", "Service", "HardwareID", "CompatibleID"]):
                ids = _as_list(ent.HardwareID) + _as_list(ent.CompatibleID)
                vp = parse_vid_pid(ent.DeviceID or "", ids)
                if not vp:
                    continue
                kind = classify_node(ent.DeviceID or "", ent.Name or "", ent.PNPClass or "", ent.Service or "", ids)
                if kind in ("keyboard", "mouse", "hid"):
                    key = f"{vp[0]}:{vp[1]}"
                    if key not in self._allowlist:
                        self._allowlist[key] = {"description": ent.Name or "", "added": _utcnow(), "note": "baseline"}
                        count += 1
        except Exception as exc:  # noqa: BLE001 - WMI raises COM errors of many types
            logger.error("Baseline scan failed: %s", exc)
        self._save_allowlist()
        logger.info("HID baseline created with %d trusted peripheral(s)", count)

    # ── main thread loop ───────────────────────────────────────────────────
    def _run(self) -> None:
        import pythoncom
        import wmi

        pythoncom.CoInitialize()  # COM must be initialised in every thread that uses WMI
        try:
            while not self._stop.is_set():
                try:
                    c = wmi.WMI()
                    self._learn_baseline_if_first_run(c)
                    watcher = c.watch_for(raw_wql=_WQL)
                    logger.info("HID guard listening for USB hardware events")
                    self._listen(c, watcher, wmi)
                except Exception as exc:  # noqa: BLE001
                    logger.error("HID guard error: %s — restarting in 5s", exc)
                    self._stop.wait(5)
        finally:
            pythoncom.CoUninitialize()

    def _listen(self, c: Any, watcher: Any, wmi_mod: Any) -> None:
        while not self._stop.is_set():
            try:
                event = watcher(timeout_ms=1000)
                self._ingest(event)
            except wmi_mod.x_wmi_timed_out:
                pass
            self._flush(c)

    def _ingest(self, ent: Any) -> None:
        device_id = getattr(ent, "DeviceID", "") or ""
        ids = _as_list(getattr(ent, "HardwareID", None)) + _as_list(getattr(ent, "CompatibleID", None))
        name = getattr(ent, "Name", "") or getattr(ent, "Description", "") or ""
        kind = classify_node(device_id, name, getattr(ent, "PNPClass", "") or "",
                             getattr(ent, "Service", "") or "", ids)
        now = time.time()

        if kind == "storage":
            with self._lock:
                self._recent_storage = [t for t in self._recent_storage if now - t < 30] + [now]
            return

        vp = parse_vid_pid(device_id, ids)
        if not vp:
            return
        node = {
            "device_id": device_id,
            "description": name,
            "manufacturer": getattr(ent, "Manufacturer", "") or "",
            "pnp_class": getattr(ent, "PNPClass", "") or "",
            "service": getattr(ent, "Service", "") or "",
            "kind": kind,
        }
        m = _SERIAL_RE.match(device_id)
        if m and "&" not in m.group(1):  # '&' in the instance part means Windows-generated, not a real serial
            node["serial"] = m.group(1)
        with self._lock:
            entry = self._pending.setdefault(vp, {"first": now, "last": now, "nodes": []})
            entry["last"] = now
            entry["nodes"].append(node)

    def _flush(self, c: Any) -> None:
        now = time.time()
        with self._lock:
            ready = [k for k, v in self._pending.items() if now - v["last"] >= _SETTLE_SECONDS]
            batches = {k: self._pending.pop(k) for k in ready}
            storage_near = {k: any(batches[k]["first"] - 30 <= t <= now for t in self._recent_storage)
                            for k in batches}
        for (vid, pid), entry in batches.items():
            try:
                self._evaluate(c, vid, pid, entry, storage_near[(vid, pid)])
            except Exception as exc:  # noqa: BLE001
                logger.exception("HID evaluation failed for %s:%s: %s", vid, pid, exc)

    # ── analysis ───────────────────────────────────────────────────────────
    def _evaluate(self, c: Any, vid: str, pid: str, entry: dict[str, Any], has_storage: bool) -> None:
        nodes = entry["nodes"]
        kinds = {n["kind"] for n in nodes}
        if not kinds & {"keyboard", "mouse", "hid"}:
            logger.debug("USB %s:%s has no HID interface — ignored by HID guard", vid, pid)
            return

        has_kb = "keyboard" in kinds
        has_mouse = "mouse" in kinds
        trusted = self.is_trusted(vid, pid)
        primary = next((n for n in nodes if n["kind"] in ("keyboard", "mouse")), nodes[0])
        description = primary["description"] or "Unknown HID device"
        reasons: list[str] = []
        score = 0

        if not trusted:
            if has_kb:
                score += 70
                reasons.append("unrecognized_keyboard")
            elif has_mouse:
                score += 30
                reasons.append("unrecognized_mouse")
            else:
                score += 15
                reasons.append("unrecognized_hid")
        if has_kb and has_storage:
            score += 25
            reasons.append("composite_keyboard_plus_storage")
        if has_kb and has_mouse:
            score += 10
            reasons.append("composite_keyboard_plus_mouse")
        if vid in _MAKER_VIDS:
            score += 15 if not trusted else 0
            reasons.append(f"maker_board_vendor:{_MAKER_VIDS[vid]}")
        if not (primary.get("manufacturer") or "").strip() or "(standard" in (primary.get("manufacturer") or "").lower():
            if not trusted:
                score += 5
                reasons.append("generic_or_missing_manufacturer")
        score = min(score, 100)

        if trusted and score < 25:
            logger.info("Trusted HID connected: %s:%s (%s)", vid, pid, description)
            self._send_telemetry("usb_hid_connected", vid, pid, description, nodes, trusted, score, "info",
                                 reasons, action={"taken": "none"}, alert=False)
            return

        severity = "critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 40 else "low"
        action = {"taken": "none", "auto_block_enabled": bool(self.settings.usb_hid_auto_block)}
        if self.settings.usb_hid_auto_block and score >= 60 and not trusted:
            action.update(self._block(c, vid, pid, nodes))

        self._send_telemetry("usb_hid_anomaly", vid, pid, description, nodes, trusted, score, severity,
                             reasons, action=action, alert=True)

    def _block(self, c: Any, vid: str, pid: str, nodes: list[dict[str, Any]]) -> dict[str, Any]:
        """Disable the device's HID nodes. Refuses if it would leave the machine without a keyboard."""
        try:
            other_keyboards = [k for k in c.Win32_Keyboard() if (k.DeviceID or "") not in {n["device_id"] for n in nodes}]
        except Exception:  # noqa: BLE001
            other_keyboards = []
        if not other_keyboards:
            return {"taken": "block_skipped", "detail": "no other keyboard present; refusing to lock the user out"}

        disabled: list[str] = []
        for n in nodes:
            if n["kind"] in ("keyboard", "mouse", "hid") and self._pnputil("disable-device", n["device_id"]):
                disabled.append(n["device_id"])
        if disabled:
            with self._lock:
                self._disabled.setdefault(f"{vid}:{pid}", []).extend(disabled)
            return {"taken": "disabled", "instance_ids": disabled}
        return {"taken": "block_failed", "detail": "pnputil failed (admin rights / Windows version?)"}

    @staticmethod
    def _pnputil(verb: str, instance_id: str) -> bool:
        try:
            r = subprocess.run(
                ["pnputil", f"/{verb}", instance_id],
                capture_output=True, text=True, timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if r.returncode != 0:
                logger.error("pnputil /%s %s failed: %s", verb, instance_id, (r.stdout or r.stderr).strip()[:200])
            return r.returncode == 0
        except (OSError, subprocess.SubprocessError) as exc:
            logger.error("pnputil error: %s", exc)
            return False

    # ── telemetry ──────────────────────────────────────────────────────────
    def build_payload(self, event_type: str, vid: str, pid: str, description: str, nodes: list[dict[str, Any]],
                      trusted: bool, score: int, severity: str, reasons: list[str],
                      action: dict[str, Any]) -> dict[str, Any]:
        serial = next((n["serial"] for n in nodes if n.get("serial")), None)
        return {
            "schema_version": 1,
            "event_type": event_type,
            "timestamp": _utcnow(),
            "host": {"hostname": socket.gethostname(), "agent_version": self.settings.agent_version},
            "device": {
                "vid": vid,
                "pid": pid,
                "vid_pid": f"{vid}:{pid}",
                "description": description,
                "manufacturer": next((n["manufacturer"] for n in nodes if n["manufacturer"]), ""),
                "serial": serial,
                "interfaces": sorted({n["kind"] for n in nodes}),
                "nodes": [{k: n[k] for k in ("device_id", "description", "pnp_class", "kind")} for n in nodes],
            },
            "verdict": {
                "trusted": trusted,
                "risk_score": score,
                "severity": severity,
                "reasons": reasons,
            },
            "action": action,
        }

    def _send_telemetry(self, event_type: str, vid: str, pid: str, description: str, nodes: list[dict[str, Any]],
                        trusted: bool, score: int, severity: str, reasons: list[str],
                        action: dict[str, Any], alert: bool) -> None:
        payload = self.build_payload(event_type, vid, pid, description, nodes, trusted, score, severity,
                                     reasons, action)
        msg = f"USB HID {'anomaly' if alert else 'connected'}: {description} [{vid}:{pid}] score={score}"
        logger.warning(msg) if alert else logger.info(msg)
        self.client.send_log(msg, category="usb", severity=severity, source="usb_hid_guard", raw_payload=payload)
        if alert:
            detail = (
                f"{description} (VID {vid.upper()} / PID {pid.upper()}) was plugged in and is not on the "
                f"trusted peripheral list.\nReasons: {', '.join(reasons)}\nAction: {action.get('taken')}"
            )
            self.alerts.notify(
                "Possible BadUSB / Rubber Ducky device",
                detail,
                severity=severity if severity != "low" else "medium",
                rule_name="usb_badusb_hid",
                popup=True,
            )
