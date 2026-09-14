"""
Isolation system — SAFE SIMULATION ONLY.

Does not execute firewall rules, iptables, or process kills.
Maintains in-memory simulation state for audit and API responses.
"""

from datetime import datetime, timezone
from typing import Any

import psutil

from app.utils.logger import get_logger

logger = get_logger("isolation_service")

# In-memory simulation registry (per device)
_isolation_state: dict[str, dict[str, Any]] = {}


class IsolationService:
    """Simulate network block, quarantine, and suspicious process review."""

    def isolate_device(
        self,
        device_id: str,
        *,
        reason: str = "threat_detected",
        block_network: bool = True,
        quarantine: bool = True,
        review_processes: bool = True,
    ) -> dict[str, Any]:
        """
        Simulate isolation workflow without destructive system commands.
        """
        logger.warning(
            "[SIMULATION] Isolating device %s (network=%s quarantine=%s)",
            device_id,
            block_network,
            quarantine,
        )

        simulated_processes: list[dict[str, Any]] = []
        if review_processes:
            # Read-only process listing — no kill signals
            for proc in psutil.process_iter(["pid", "name", "username"]):
                try:
                    info = proc.info
                    name = (info.get("name") or "").lower()
                    if any(k in name for k in ("encrypt", "ransom", "miner", "suspicious")):
                        simulated_processes.append(
                            {
                                "pid": info.get("pid"),
                                "name": info.get("name"),
                                "action": "simulated_quarantine_flag",
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        state = {
            "device_id": device_id,
            "isolated": True,
            "reason": reason,
            "isolated_at": datetime.now(timezone.utc).isoformat(),
            "simulation": True,
            "actions": {
                "network_blocked": block_network,
                "device_quarantined": quarantine,
                "processes_flagged": len(simulated_processes),
            },
            "flagged_processes": simulated_processes[:20],
            "note": "Simulation only — no real network or process changes applied",
        }
        _isolation_state[device_id] = state
        logger.info("[SIMULATION] Device %s isolation state recorded", device_id)
        return state

    def release_device(self, device_id: str) -> dict[str, Any]:
        """Simulate lifting isolation."""
        prev = _isolation_state.pop(device_id, None)
        logger.info("[SIMULATION] Released isolation for %s", device_id)
        return {
            "device_id": device_id,
            "isolated": False,
            "released_at": datetime.now(timezone.utc).isoformat(),
            "previous_state": prev,
        }

    def get_status(self, device_id: str) -> dict[str, Any]:
        return _isolation_state.get(
            device_id,
            {"device_id": device_id, "isolated": False, "simulation": True},
        )

    def list_isolated(self) -> list[dict[str, Any]]:
        return [s for s in _isolation_state.values() if s.get("isolated")]
