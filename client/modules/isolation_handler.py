"""Production-ready isolation handler using Windows Firewall ("Lifeboat" strategy).

Isolates the endpoint at the firewall level so *all* network traffic is blocked
except:
  - DHCP  (UDP 67/68)   — so the NIC keeps its lease
  - DNS   (UDP+TCP 53)  — so the agent can still resolve the backend hostname
  - Defendra API (TCP 443 & 8000) — so the agent can receive the "recover" command

On recovery the quarantine rules are removed and the default outbound policy is
restored to ALLOW.

Requires **elevated (Administrator)** privileges on Windows.
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import psutil

if TYPE_CHECKING:
    from core.api_client import DefendraClient
    from modules.alert_system import AlertSystem

logger = logging.getLogger("client.isolation")

# ── Constants ────────────────────────────────────────────────────────────────

# Prefix for every firewall rule we create — makes cleanup deterministic
_FW_PREFIX = "DefendraQuarantine"

# Critical system processes that should NOT be terminated
SYSTEM_CRITICAL_PROCESSES = {
    # Windows critical processes
    "System", "Registry", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "svchost.exe", "winlogon.exe",
    "dwm.exe", "explorer.exe",
    # Linux critical processes
    "systemd", "init", "kthreadd", "migration", "ksoftirqd",
    "watchdog", "khungtaskd", "kworker", "systemd-journald",
}

# Persistent state file so the agent remembers it is quarantined across restarts
_STATE_DIR = Path(__file__).resolve().parent.parent / "data"
_QUARANTINE_FLAG = _STATE_DIR / "quarantine_active.flag"


# ── Windows helpers ──────────────────────────────────────────────────────────

def _is_admin() -> bool:
    """Return True when the current process has Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run_netsh(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a netsh command and return the CompletedProcess. Logs on failure."""
    cmd = ["netsh"] + list(args)
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        logger.warning("netsh exit %d | stderr: %s", result.returncode, result.stderr.strip())
    return result


def _delete_defendra_rules() -> int:
    """Delete every firewall rule whose name starts with the Defendra prefix.

    Returns the number of rules removed.
    """
    result = _run_netsh(
        "advfirewall", "firewall", "show", "rule",
        f"name=all", "verbose",
    )
    removed = 0
    for line in result.stdout.splitlines():
        if line.startswith("Rule Name:"):
            rule_name = line.split(":", 1)[1].strip()
            if rule_name.startswith(_FW_PREFIX):
                _run_netsh("advfirewall", "firewall", "delete", "rule", f"name={rule_name}")
                logger.info("Deleted firewall rule: %s", rule_name)
                removed += 1
    return removed


def _add_allow_rule(
    name: str,
    *,
    direction: str,
    protocol: str,
    localport: str | None = None,
    remoteport: str | None = None,
) -> None:
    """Add a single ALLOW rule with the Defendra prefix."""
    full_name = f"{_FW_PREFIX}_{name}"
    cmd = [
        "advfirewall", "firewall", "add", "rule",
        f"name={full_name}",
        f"dir={direction}",
        "action=allow",
        f"protocol={protocol}",
        "enable=yes",
    ]
    if localport:
        cmd.append(f"localport={localport}")
    if remoteport:
        cmd.append(f"remoteport={remoteport}")
    _run_netsh(*cmd)
    logger.info("Added firewall rule: %s (dir=%s proto=%s)", full_name, direction, protocol)


# ── Core firewall isolation / recovery ───────────────────────────────────────

def firewall_isolate() -> bool:
    """Apply the full Windows Firewall quarantine ("Lifeboat" strategy).

    Steps:
      1. Delete any stale DefendraQuarantine rules.
      2. Set default policy: block inbound AND outbound.
      3. Add ALLOW rules for DHCP, DNS, and Defendra API traffic.

    Returns True on success.
    """
    if platform.system() != "Windows":
        logger.error("Firewall isolation is only supported on Windows")
        return False

    if not _is_admin():
        logger.error("Firewall isolation requires Administrator privileges")
        return False

    logger.critical("=== APPLYING FIREWALL QUARANTINE ===")

    # 1. Clean slate — remove previous quarantine rules if any
    _delete_defendra_rules()

    # 2. Default policy: BLOCK everything in both directions
    _run_netsh("advfirewall", "set", "allprofiles", "firewallpolicy", "blockinbound,blockoutbound")
    logger.info("Default firewall policy set to BLOCK inbound + outbound")

    # 3a. DHCP — allow client to renew its IP lease
    _add_allow_rule("DHCP_Out", direction="out", protocol="udp", remoteport="67")
    _add_allow_rule("DHCP_In",  direction="in",  protocol="udp", localport="68")

    # 3b. DNS — allow name resolution so the agent can reach the backend by hostname
    _add_allow_rule("DNS_Out_UDP", direction="out", protocol="udp", remoteport="53")
    _add_allow_rule("DNS_Out_TCP", direction="out", protocol="tcp", remoteport="53")
    _add_allow_rule("DNS_In_UDP",  direction="in",  protocol="udp", localport="53")
    _add_allow_rule("DNS_In_TCP",  direction="in",  protocol="tcp", localport="53")

    # 3c. Defendra API — HTTPS (443) + dev port (8000)
    _add_allow_rule("API_Out_443",  direction="out", protocol="tcp", remoteport="443")
    _add_allow_rule("API_In_443",   direction="in",  protocol="tcp", localport="443")
    _add_allow_rule("API_Out_8000", direction="out", protocol="tcp", remoteport="8000")
    _add_allow_rule("API_In_8000",  direction="in",  protocol="tcp", localport="8000")

    # Persist quarantine flag so it survives agent restarts
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _QUARANTINE_FLAG.write_text("1", encoding="utf-8")

    logger.critical("=== FIREWALL QUARANTINE ACTIVE ===")
    return True


def firewall_recover() -> bool:
    """Remove the quarantine and restore normal firewall policy.

    Steps:
      1. Delete all DefendraQuarantine rules.
      2. Restore default policy: block inbound, ALLOW outbound.

    Returns True on success.
    """
    if platform.system() != "Windows":
        logger.error("Firewall recovery is only supported on Windows")
        return False

    if not _is_admin():
        logger.error("Firewall recovery requires Administrator privileges")
        return False

    logger.critical("=== REMOVING FIREWALL QUARANTINE ===")

    # 1. Remove every rule we added
    _delete_defendra_rules()

    # 2. Restore the sensible Windows default: block inbound, allow outbound
    _run_netsh("advfirewall", "set", "allprofiles", "firewallpolicy", "blockinbound,allowoutbound")
    logger.info("Default firewall policy restored to BLOCK inbound / ALLOW outbound")

    # Remove quarantine flag
    _QUARANTINE_FLAG.unlink(missing_ok=True)

    logger.critical("=== FIREWALL QUARANTINE REMOVED ===")
    return True


def is_quarantine_active() -> bool:
    """Check if a quarantine flag is persisted (survives agent restart)."""
    return _QUARANTINE_FLAG.is_file()


# ── Main handler class (unchanged public interface) ──────────────────────────

class IsolationHandler:
    """Executes isolation commands with configurable grace period.

    Uses real Windows Firewall rules ("Lifeboat" strategy) instead of
    disabling network interfaces so the agent can still phone home.
    """

    def __init__(self, client: DefendraClient, alerts: AlertSystem):
        self.client = client
        self.alerts = alerts
        self._countdown_thread: threading.Thread | None = None
        self._cancel_flag = threading.Event()
        self._isolated = False

        # If the agent restarts while quarantined, stay quarantined
        if is_quarantine_active():
            self._isolated = True
            logger.warning("Agent restarted while quarantine was active — keeping firewall rules")

    @property
    def isolated(self) -> bool:
        return self._isolated

    # ── Public: called by CommandHandler or autonomic triggers ───────────

    def execute_isolation(
        self,
        isolation_type: str,
        grace_period: int,
        reason: str,
        isolated_by: str,
    ) -> None:
        """
        Execute isolation with countdown.
        
        Args:
            isolation_type: "network_only" or "full_shutdown"
            grace_period: Seconds before isolation takes effect
            reason: Admin-provided reason
            isolated_by: Admin email or "autonomic"
        """
        logger.critical(
            "ISOLATION COMMAND RECEIVED: type=%s grace=%ds reason=%s by=%s",
            isolation_type, grace_period, reason, isolated_by,
        )
        
        # Show critical alert
        self.alerts.notify(
            title="DEVICE ISOLATED",
            message=(
                f"This device has been isolated by {isolated_by}.\nReason: {reason}\n"
                f"{'Network will be quarantined' if isolation_type == 'network_only' else 'System will shut down'} "
                f"in {grace_period} seconds."
            ),
            severity="critical",
            rule_name="isolation",
        )

        # Log to server (still reachable via Lifeboat rules)
        self.client.send_log(
            f"Device isolation started: {isolation_type}, grace period: {grace_period}s",
            category="isolation",
            severity="critical",
            source="isolation_handler",
        )
        
        # Start countdown thread
        self._cancel_flag.clear()
        self._countdown_thread = threading.Thread(
            target=self._countdown_and_execute,
            args=(isolation_type, grace_period, reason),
            daemon=True,
        )
        self._countdown_thread.start()

    def execute_immediate_isolation(self, reason: str) -> bool:
        """Bypass the countdown and quarantine the network **right now**.

        Designed for autonomic containment (e.g. ransomware detector) where
        every second counts.
        """
        logger.critical("IMMEDIATE ISOLATION triggered: %s", reason)
        ok = firewall_isolate()
        if ok:
            self._isolated = True
            self.client.send_log(
                f"Immediate network quarantine applied: {reason}",
                category="isolation",
                severity="critical",
                source="isolation_handler",
            )
        else:
            logger.error("Immediate firewall isolation FAILED")
        return ok

    def execute_recovery(self) -> bool:
        """Remove quarantine rules and restore normal connectivity."""
        logger.critical("RECOVERY triggered")
        ok = firewall_recover()
        if ok:
            self._isolated = False
            self.client.send_log(
                "Firewall quarantine removed — normal connectivity restored",
                category="isolation",
                severity="info",
                source="isolation_handler",
            )
        else:
            logger.error("Firewall recovery FAILED")
        return ok

    # ── Countdown logic ──────────────────────────────────────────────────

    def _countdown_and_execute(self, isolation_type: str, grace_period: int, reason: str) -> None:
        """Countdown with periodic notifications, then execute isolation."""

        for remaining in range(grace_period, 0, -1):
            if self._cancel_flag.is_set():
                logger.info("Isolation cancelled by server")
                self.alerts.notify(
                    "Isolation Cancelled",
                    "Admin has cancelled the isolation command.",
                    severity="warning",
                    rule_name="isolation",
                )
                return

            if remaining in (60, 30, 10, 5) or remaining <= 5:
                logger.warning("Isolation in %d seconds...", remaining)
                action = "Shutdown" if isolation_type == "full_shutdown" else "Network quarantine"
                self.alerts.notify(
                    f"Isolation in {remaining}s",
                    f"{action} in {remaining} seconds.",
                    severity="critical",
                    rule_name="isolation",
                )
            
            time.sleep(1)
        
        # ── Execute isolation ────────────────────────────────────────────
        logger.critical("Executing %s isolation", isolation_type)

        if isolation_type == "network_only":
            ok = firewall_isolate()
            if ok:
                self._isolated = True
            self.client.send_log(
                f"Network quarantine {'applied' if ok else 'FAILED'}: {reason}",
                category="isolation",
                severity="critical",
                source="isolation_handler",
            )

        elif isolation_type == "full_shutdown":
            firewall_isolate()
            self._isolated = True
            self._terminate_processes()
            self._shutdown_system(reason)

    # ── Full-shutdown helpers (unchanged) ────────────────────────────────

    def _terminate_processes(self) -> None:
        """Terminate all non-critical processes."""
        logger.critical("Terminating non-critical processes")
        
        terminated_count = 0
        current_pid = os.getpid()
        
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = proc.info["name"]
                proc_pid = proc.info["pid"]

                if proc_name in SYSTEM_CRITICAL_PROCESSES:
                    continue
                if proc_pid == current_pid:
                    continue
                if platform.system() == "Linux" and proc_pid < 100:
                    continue
                if platform.system() == "Windows" and proc_pid < 1000:
                    continue

                logger.debug("Terminating %s (PID: %d)", proc_name, proc_pid)
                proc.terminate()
                terminated_count += 1
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        time.sleep(2)

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] not in SYSTEM_CRITICAL_PROCESSES:
                    if proc.info["pid"] != current_pid:
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        logger.info("Terminated %d processes", terminated_count)

    def _shutdown_system(self, reason: str) -> None:
        """Shut down the system."""
        logger.critical("Initiating system shutdown")
        system = platform.system()
        
        try:
            self.client.send_log(
                f"System shutdown initiated: {reason}",
                category="isolation",
                severity="critical",
                source="isolation_handler",
            )
            
            if system == "Windows":
                subprocess.run(
                    ["shutdown", "/s", "/t", "0", "/f", "/c", f"Device isolated: {reason}"],
                    check=True,
                )
            elif system == "Linux":
                subprocess.run(
                    ["shutdown", "-h", "now", f"Device isolated: {reason}"],
                    check=True,
                )
            
        except Exception as e:
            logger.error("Shutdown failed: %s", e)

    def cancel_isolation(self) -> None:
        """Cancel an ongoing isolation countdown (admin override)."""
        self._cancel_flag.set()
        logger.info("Isolation cancellation requested")
