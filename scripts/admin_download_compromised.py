#!/usr/bin/env python3
"""
admin_download_compromised.py — Defendra Secure Admin Recovery CLI.

This tool allows an authorized enterprise admin / employer to securely
retrieve the quarantined backup ZIP of a *compromised* device directly
from Firebase Cloud Storage using privileged Service Account credentials.

4-Step automated workflow
  Step 1  Authenticate via Firebase Admin SDK (Service Account Key)
  Step 2  Sanitize target paths to enforce absolute isolation boundaries
  Step 3  Download the .zip archive to the admin's secure local folder
  Step 4  Update the Defendra dashboard audit log with the download event

Any step failure throws a strict security exception and aborts the entire
process — no partial data is left and no information is leaked.

Usage
  python scripts/admin_download_compromised.py \\
      --admin-id  "admin_jane"         \\
      --device-id "PC-Finance-01"      \\
      --backup-id "bk_20260930_143012_a1b2c3d4" \\
      --output-dir "C:/SecureRecovery"

Required environment variables (set in .env or shell before running):
  FIREBASE_SERVICE_ACCOUNT_JSON   Path to service-account .json OR raw JSON
  FIREBASE_STORAGE_BUCKET         e.g. defendra-backups.appspot.com

Optional:
  ADMIN_DOWNLOAD_DIR              Override default output directory
  DEFENDRA_API_URL                Defendra backend URL for audit forwarding
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: ensure recovery_automation package root is on sys.path so this
# script can be run from ANY working directory.
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent          # scripts/
_PROJECT_ROOT = _SCRIPT_DIR.parent                      # defendra-main/
_RECOVERY_MODULE = _PROJECT_ROOT / "recovery_automation"

if str(_RECOVERY_MODULE) not in sys.path:
    sys.path.insert(0, str(_RECOVERY_MODULE))

# Load .env from the recovery_automation module (non-fatal if missing)
try:
    from dotenv import load_dotenv  # type: ignore[import-untyped]
    _env_file = _RECOVERY_MODULE / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass  # rely on shell env vars

# ---------------------------------------------------------------------------
# Import the privileged service (after path bootstrap)
# ---------------------------------------------------------------------------

try:
    from app.services.admin_firebase_service import (
        AdminFirebaseService,
        AdminSecurityException,
    )
    from app.utils.logger import get_logger
except ImportError as exc:
    print(
        f"\n[FATAL] Could not import Defendra recovery modules: {exc}\n"
        "Ensure you are running from the project root or that "
        "recovery_automation/ is on your PYTHONPATH.\n",
        file=sys.stderr,
    )
    sys.exit(2)

logger = get_logger("admin_download_cli")

# ---------------------------------------------------------------------------
# ANSI colour helpers (gracefully degrades on terminals without colour)
# ---------------------------------------------------------------------------

_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def _green(t: str) -> str: return _c("32;1", t)
def _red(t: str) -> str: return _c("31;1", t)
def _yellow(t: str) -> str: return _c("33;1", t)
def _cyan(t: str) -> str: return _c("36;1", t)
def _bold(t: str) -> str: return _c("1", t)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

_BANNER = """
+==================================================================+
|        DEFENDRA - SECURE ADMIN COMPROMISE-RECOVERY TOOL          |
|  Zero-Trust  |  Firebase Admin SDK  |  AES-256  |  Audit Log     |
+==================================================================+
"""


def _print_banner() -> None:
    print(_cyan(_BANNER))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="admin_download_compromised",
        description=textwrap.dedent("""\
            Defendra - Secure Admin Compromise-Recovery Download Tool.

            Downloads a quarantined backup ZIP from Firebase Cloud Storage
            for a compromised device using privileged Service Account creds.
            All interactions are audit-logged locally and on the dashboard.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              python scripts/admin_download_compromised.py \\
                  --admin-id admin_jane \\
                  --device-id PC-Finance-01 \\
                  --backup-id bk_20260930_143012_a1b2c3d4

              python scripts/admin_download_compromised.py \\
                  --admin-id admin_bob \\
                  --device-id LAPTOP-HR-07 \\
                  --backup-id bk_20261005_090000_deadbeef \\
                  --output-dir "C:/SecureRecovery/HR"
        """),
    )
    parser.add_argument(
        "--admin-id",
        required=True,
        metavar="ADMIN_ID",
        help=(
            "Identifier of the admin / employer initiating this download. "
            "Recorded verbatim in the audit log. "
            "Allowed characters: a-z A-Z 0-9 _ -"
        ),
    )
    parser.add_argument(
        "--device-id",
        required=True,
        metavar="DEVICE_ID",
        help=(
            "ID of the compromised device whose backup is to be retrieved. "
            "Must match the device_id used when the backup was created. "
            "Allowed characters: a-z A-Z 0-9 _ -"
        ),
    )
    parser.add_argument(
        "--backup-id",
        required=True,
        metavar="BACKUP_ID",
        help=(
            "Specific backup archive ID (e.g. bk_20260930_143012_a1b2c3d4). "
            "The service will look for backups/{device-id}/{backup-id}.zip. "
            "Allowed characters: a-z A-Z 0-9 _ -"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="OUTPUT_DIR",
        help=(
            "Local directory where the downloaded ZIP will be saved. "
            "Defaults to ADMIN_DOWNLOAD_DIR env var or "
            "<recovery_automation>/admin_downloads/."
        ),
    )
    return parser



# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns 0 on success, 1 on security failure, 2 on bad args."""
    _print_banner()

    parser = _build_parser()
    args = parser.parse_args(argv)

    admin_id = args.admin_id
    device_id = args.device_id
    backup_id = args.backup_id
    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else None
    )

    # Print job summary
    print(_bold("=" * 66))
    print(f"  Admin ID  : {_yellow(admin_id)}")
    print(f"  Device ID : {_yellow(device_id)}")
    print(f"  Backup ID : {_yellow(backup_id)}")
    out_display = str(output_dir) if output_dir else "(default: admin_downloads/)"
    print(f"  Output    : {_yellow(out_display)}")
    print(_bold("=" * 66))
    print()

    # ── Pre-flight environment check ─────────────────────────────────
    missing_vars: list[str] = []
    for var in ("FIREBASE_SERVICE_ACCOUNT_JSON", "FIREBASE_STORAGE_BUCKET"):
        if not os.environ.get(var, "").strip():
            missing_vars.append(var)

    if missing_vars:
        print(_red("[ERROR] The following required environment variables are not set:"))
        for v in missing_vars:
            print(_red(f"  * {v}"))
        print(
            _yellow(
                "\nSet them in recovery_automation/.env or export them in your "
                "shell before running this tool.\n"
            )
        )
        logger.error("Missing environment variables: %s", missing_vars)
        return 1

    # ── Announce 4-step workflow ──────────────────────────────────────
    print(_bold("Starting 4-step secure download workflow...\n"))
    print(f"  {_bold('Step 1')}: Authenticate via Firebase Admin SDK (Service Account)...")
    print(f"  {_bold('Step 2')}: Sanitize target paths (zero-trust isolation boundary)...")
    print(f"  {_bold('Step 3')}: Download quarantined backup from Firebase Cloud Storage...")
    print(f"  {_bold('Step 4')}: Record tamper-evident audit log...\n")

    # ── Execute ───────────────────────────────────────────────────────
    service = AdminFirebaseService()
    try:
        result = service.download_compromised_backup(
            admin_id=admin_id,
            device_id=device_id,
            backup_id=backup_id,
            output_dir=output_dir,
        )
    except AdminSecurityException as exc:
        print(_red("\n+-- SECURITY EXCEPTION - WORKFLOW ABORTED --+"))
        for line in textwrap.wrap(str(exc), width=60):
            print(_red(f"  {line}"))
        print(_red("+-------------------------------------------+\n"))
        logger.error("Admin download aborted with security exception: %s", exc)
        return 1
    except Exception as exc:
        print(_red(f"\n[FATAL] Unexpected error: {exc}\n"))
        logger.exception("Unexpected error in admin_download_compromised")
        return 1

    # ── Success ───────────────────────────────────────────────────────
    size_mb = result["size_bytes"] / (1024 * 1024)
    print(_green("\n+-- DOWNLOAD SUCCESSFUL -------------------------------------------+"))
    print(_green(f"  Admin     : {result['admin_id']}"))
    print(_green(f"  Device    : {result['device_id']}"))
    print(_green(f"  Backup    : {result['backup_id']}"))
    print(_green(f"  Blob path : {result['blob_path']}"))
    print(_green(f"  Saved to  : {result['local_file']}"))
    print(_green(f"  Size      : {size_mb:.2f} MB ({result['size_bytes']:,} bytes)"))
    print(_green(f"  Timestamp : {result['timestamp']}"))
    print(_green(f"  Outcome   : {result['outcome']}"))
    print(_green("+------------------------------------------------------------------+\n"))

    audit_log = _RECOVERY_MODULE / "logs" / "admin_audit.log"
    print(_yellow(f"Audit log : {audit_log}"))
    print(_yellow("Dashboard : Defendra backend (if reachable)\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

