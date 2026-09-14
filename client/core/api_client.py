"""REST communication with the Defendra backend."""

from __future__ import annotations

import logging
import platform
import socket
import time
import uuid
from typing import Any

import requests

from config.settings import get_settings
from core.location import resolve_device_location
from core.offline_queue import OfflineQueue

logger = logging.getLogger("client.api")


class DefendraClient:
    """
    Server communication layer.

    Implements send_log(), send_alert(), fetch_commands(), device registration,
    heartbeat, and offline sync against the existing Defendra API.
    """

    def __init__(self, queue: OfflineQueue | None = None) -> None:
        self.settings = get_settings()
        self.queue = queue or OfflineQueue()
        self._token: str | None = None
        self._token_at: float = 0.0
        self._device_id: str | None = self._load_device_id()
        self._last_commands: list[dict[str, Any]] = []
        self._cached_location: str | None = None
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ── Public API (required by spec) ───────────────────────────────────────

    def send_log(
        self,
        message: str,
        *,
        category: str = "agent",
        severity: str = "info",
        source: str = "client_agent",
        raw_payload: dict[str, Any] | None = None,
    ) -> bool:
        """POST /api/logs — queues locally if offline or device missing."""
        device_id = self._device_id or self.ensure_device()
        payload = {
            "device_id": device_id or "",
            "category": category,
            "severity": severity,
            "source": source,
            "message": message,
            "raw_payload": raw_payload or {},
        }

        if not device_id or not self.is_server_reachable():
            self.queue.enqueue_log(payload)
            if not device_id:
                logger.debug("Log queued (no device_id yet): %s", message[:80])
            else:
                logger.info("Log queued (offline): %s", message[:80])
            return False

        try:
            resp = self._session.post(
                f"{self.settings.api_base}/logs",
                json=payload,
                timeout=12,
            )
            if resp.status_code in (200, 201):
                return True
            logger.error("send_log HTTP %s: %s", resp.status_code, resp.text[:200])
            self.queue.enqueue_log(payload)
            return False
        except requests.RequestException as exc:
            logger.error("send_log failed: %s", exc)
            self.queue.enqueue_log(payload)
            return False

    def send_alert(
        self,
        title: str,
        description: str,
        *,
        severity: str = "high",
        rule_name: str = "client_agent",
    ) -> bool:
        """POST /api/alerts — requires JWT; queues if offline."""
        device_id = self.ensure_device()
        payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "severity": severity,
            "status": "open",
            "rule_name": rule_name,
        }
        if device_id:
            payload["device_id"] = device_id

        if not self.is_server_reachable():
            self.queue.enqueue_alert(payload)
            return False

        try:
            resp = self._session.post(
                f"{self.settings.api_base}/alerts",
                json=payload,
                headers=self._auth_headers(),
                timeout=12,
            )
            if resp.status_code in (200, 201):
                return True
            logger.error("send_alert HTTP %s: %s", resp.status_code, resp.text[:200])
            self.queue.enqueue_alert(payload)
            return False
        except requests.RequestException as exc:
            logger.error("send_alert failed: %s", exc)
            self.queue.enqueue_alert(payload)
            return False

    def fetch_commands(self) -> list[dict[str, Any]]:
        """
        Poll server for admin-driven commands.

        Maps device status from GET /api/devices to actionable commands:
          isolated  -> isolate
          limpmode  -> limp_mode
          offline   -> mark_offline (informational)

        Also reads optional local test commands from data/pending_commands.json.
        """
        commands: list[dict[str, Any]] = []
        device_id = self.device_id

        # Local simulation file for testing without admin UI changes
        sim_path = self.settings.data_dir / "pending_commands.json"
        if sim_path.exists():
            try:
                import json

                local = json.loads(sim_path.read_text(encoding="utf-8"))
                if isinstance(local, list):
                    commands.extend(local)
                sim_path.unlink(missing_ok=True)
            except (OSError, json.JSONDecodeError):
                pass

        if not device_id or not self.is_server_reachable():
            self._last_commands = commands
            return commands

        try:
            resp = self._session.get(
                f"{self.settings.api_base}/devices",
                headers=self._auth_headers(),
                timeout=12,
            )
            if resp.status_code != 200:
                self._last_commands = commands
                return commands

            for device in resp.json():
                if str(device.get("id")) != str(device_id):
                    continue
                status = (device.get("status") or "").lower()
                if status == "isolated":
                    commands.append({"type": "isolate", "source": "server_status"})
                elif status in ("limpmode", "limp_mode"):
                    commands.append({"type": "limp_mode", "source": "server_status"})
                elif status == "scan_requested":
                    commands.append({"type": "scan", "source": "server_status"})
                elif status == "backup_requested":
                    commands.append({"type": "backup", "source": "server_status"})
                break
        except requests.RequestException as exc:
            logger.debug("fetch_commands failed: %s", exc)

        self._last_commands = commands
        return commands

    # ── Device lifecycle ────────────────────────────────────────────────────

    @property
    def device_id(self) -> str | None:
        return self._device_id

    def ensure_device(self) -> str | None:
        if self._device_id:
            return self._device_id
        if not self.is_server_reachable():
            return None
        return self.register_device()

    def register_device(self) -> str | None:
        """Register or link this workstation with the Defendra backend."""
        hostname = self.settings.device_name or socket.gethostname()
        os_name = f"{platform.system()} {platform.release()}"
        local_ip = self._local_ip()
        location = self._device_location(local_ip)

        if not self._get_token():
            logger.error(
                "Cannot register device — check API_EMAIL/API_PASSWORD in client\\.env "
                "(default: admin@defendra.com / Admin@1234 after running start.bat)"
            )
            return None

        # Any authenticated user can link by hostname (idempotent)
        link_payload = {
            "hostname": hostname,
            "platform": platform.system(),
            "os_name": os_name,
            "agent_version": self.settings.agent_version,
            "ip_address": local_ip,
            "location": location,
        }
        try:
            resp = self._session.post(
                f"{self.settings.api_base}/devices/workstation/link",
                json=link_payload,
                headers=self._auth_headers(),
                timeout=15,
            )
            if resp.status_code in (200, 201):
                device_id = str(resp.json().get("id", ""))
                if device_id:
                    self._device_id = device_id
                    self._save_device_id(device_id)
                    logger.info("Linked workstation device_id=%s", device_id)
                    return device_id
            logger.debug(
                "workstation/link HTTP %s: %s", resp.status_code, resp.text[:200]
            )
        except requests.RequestException as exc:
            logger.debug("workstation link failed: %s", exc)

        # Fallback: admin-only full device create
        payload = {
            "hostname": hostname,
            "ip_address": local_ip,
            "mac_address": self._mac_address(),
            "os_name": os_name,
            "agent_version": self.settings.agent_version,
            "location": location,
        }
        try:
            resp = self._session.post(
                f"{self.settings.api_base}/devices",
                json=payload,
                headers=self._auth_headers(),
                timeout=15,
            )
            if resp.status_code in (200, 201):
                device_id = str(resp.json().get("id", ""))
                if device_id:
                    self._device_id = device_id
                    self._save_device_id(device_id)
                    logger.info("Registered device_id=%s", device_id)
                    return device_id
            logger.error("register_device HTTP %s: %s", resp.status_code, resp.text[:200])
        except requests.RequestException as exc:
            logger.error("register_device failed: %s", exc)
        return None

    def send_heartbeat(self) -> bool:
        """POST /api/devices/{id}/heartbeat with CPU/RAM metrics."""
        import psutil

        device_id = self.ensure_device()
        if not device_id:
            return False

        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory().percent
        except Exception:
            cpu, ram = 0.0, 0.0

        local_ip = self._local_ip()
        payload = {
            "status": "online",
            "cpu_usage": cpu,
            "ram_usage": ram,
            "ip_address": local_ip,
            "location": self._device_location(local_ip),
        }
        url = f"{self.settings.api_base}/devices/{device_id}/heartbeat"

        try:
            resp = self._session.post(url, json=payload, timeout=12)
            if resp.status_code in (200, 201):
                return True
            if resp.status_code == 404:
                logger.warning("Device missing on server — re-registering")
                self._device_id = None
                self._clear_device_id_file()
                new_id = self.register_device()
                if new_id:
                    resp2 = self._session.post(
                        f"{self.settings.api_base}/devices/{new_id}/heartbeat",
                        json=payload,
                        timeout=12,
                    )
                    return resp2.status_code in (200, 201)
            logger.error("heartbeat HTTP %s", resp.status_code)
        except requests.RequestException as exc:
            logger.error("heartbeat failed: %s", exc)
        return False

    def sync_offline_queue(self) -> int:
        """Flush queued logs/alerts when connectivity returns."""
        device_id = self.ensure_device()
        if not device_id or not self.is_server_reachable():
            return 0

        synced = 0
        logs = self.queue.drain_logs()
        if logs:
            body = {
                "device_id": device_id,
                "logs": [
                    {
                        "device_id": device_id,
                        "category": item.get("category", "agent"),
                        "severity": item.get("severity", "info"),
                        "source": item.get("source", "client_agent"),
                        "message": item.get("message", ""),
                        "raw_payload": item.get("raw_payload") or {},
                        "queued_at": item.get("queued_at"),
                    }
                    for item in logs
                ],
            }
            try:
                resp = self._session.post(
                    f"{self.settings.api_base}/sync/offline-logs",
                    json=body,
                    timeout=20,
                )
                if resp.status_code in (200, 201):
                    synced += len(logs)
            except requests.RequestException as exc:
                for item in logs:
                    self.queue.enqueue_log(item)
                logger.error("offline log sync failed: %s", exc)

        for alert in self.queue.drain_alerts():
            ok = self.send_alert(
                alert.get("title", "Alert"),
                alert.get("description", ""),
                severity=alert.get("severity", "high"),
                rule_name=alert.get("rule_name", "client_agent"),
            )
            if ok:
                synced += 1
            else:
                self.queue.enqueue_alert(alert)
                break

        if synced:
            logger.info("Synced %s offline item(s)", synced)
        return synced

    # ── Connectivity ────────────────────────────────────────────────────────

    def is_server_reachable(self) -> bool:
        try:
            resp = self._session.get(
                f"{self.settings.server_url.rstrip('/')}/health",
                timeout=5,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def is_internet_available(self) -> bool:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return self.is_server_reachable()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _auth_headers(self) -> dict[str, str]:
        token = self._get_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _get_token(self) -> str:
        now = time.time()
        if self._token and (now - self._token_at) < 3000:
            return self._token

        if self.settings.api_token:
            self._token = self.settings.api_token
            self._token_at = now
            return self._token

        if self.settings.api_email and self.settings.api_password:
            if self.settings.api_password in ("your_password_here", "change-me"):
                logger.warning(
                    "API_PASSWORD is still a placeholder — edit client\\.env with real credentials"
                )
            try:
                resp = self._session.post(
                    f"{self.settings.api_base}/auth/login",
                    json={
                        "email": self.settings.api_email,
                        "password": self.settings.api_password,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    self._token = resp.json().get("access_token", "")
                    self._token_at = now
                    return self._token or ""
                logger.error("Login failed HTTP %s: %s", resp.status_code, resp.text[:200])
            except requests.RequestException as exc:
                logger.error("login failed: %s", exc)

        return ""

    def _device_location(self, local_ip: str | None = None) -> str:
        if self._cached_location:
            return self._cached_location
        ip = local_ip or self._local_ip()
        self._cached_location = resolve_device_location(
            override=self.settings.device_location,
            local_ip=ip,
        )
        return self._cached_location

    @staticmethod
    def _local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except OSError:
            return "127.0.0.1"

    @staticmethod
    def _mac_address() -> str | None:
        try:
            mac_int = uuid.getnode()
            mac_hex = f"{mac_int:012x}"
            return ":".join(mac_hex[i : i + 2] for i in range(0, 12, 2))
        except Exception:
            return None

    def _load_device_id(self) -> str | None:
        path = self.settings.device_id_file
        if path.is_file():
            val = path.read_text(encoding="utf-8").strip()
            return val or None
        return None

    def _save_device_id(self, device_id: str) -> None:
        self.settings.device_id_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings.device_id_file.write_text(device_id, encoding="utf-8")

    def _clear_device_id_file(self) -> None:
        try:
            self.settings.device_id_file.unlink(missing_ok=True)
        except OSError:
            pass
