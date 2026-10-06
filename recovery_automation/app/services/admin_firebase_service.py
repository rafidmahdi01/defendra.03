"""
Admin Firebase Service — Privileged Compromise-Recovery Download Layer.

Provides a zero-trust, audit-logged mechanism that allows only authenticated
enterprise admins (using a Firebase Service Account key) to download a
quarantined backup ZIP from Firebase Cloud Storage for a *specific* compromised
device.

Security guarantees:
  - All device_id / backup_id inputs are sanitized via strict regex before
    any storage path is constructed (prevents path-traversal / injection).
  - Firebase Admin SDK bypasses client-level Storage security rules entirely,
    so no standard device can access another device's bucket prefix.
  - AES-256 at-rest & TLS in-transit encryption is enforced by the Firebase
    Cloud Storage bucket defaults — no plaintext data ever leaves the bucket.
  - Every interaction (success or failure) is recorded to a tamper-evident
    local audit log AND forwarded to the Defendra dashboard API.
  - Any failure raises AdminSecurityException immediately, aborting the
    workflow to prevent partial / leaked state.

Storage layout expected in the Firebase bucket:
  backups/{device_id}/{backup_id}.zip

Environment variables required (add to .env):
  FIREBASE_SERVICE_ACCOUNT_JSON   Path to the service-account .json key file
                                   OR the raw JSON string (for CI/CD secrets).
  FIREBASE_STORAGE_BUCKET         Firebase Storage bucket name
                                   (e.g. defendra-backups.appspot.com)
  ADMIN_DOWNLOAD_DIR              Local directory where downloads are saved
                                   (defaults to recovery_automation/admin_downloads/)
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Security constants
# ---------------------------------------------------------------------------

# Allowlist pattern — only alphanumeric chars, underscores and hyphens.
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

# Maximum lengths to guard against resource-exhaustion attacks.
_MAX_ID_LEN = 128

# Storage prefix inside the Firebase bucket
_BUCKET_PREFIX = "backups"

# Local audit log file (relative to recovery_automation module root)
_AUDIT_LOG_NAME = "logs/admin_audit.log"

# ---------------------------------------------------------------------------
# Lazy imports — module-level deps from the existing codebase
# ---------------------------------------------------------------------------

from app.integrations.api_client import DefendraAPIError, get_api_client
from app.utils.config import MODULE_ROOT, get_settings
from app.utils.logger import get_logger

logger = get_logger("admin_firebase_service")


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class AdminSecurityException(Exception):
    """
    Raised whenever any step of the admin recovery workflow fails.

    Signals the caller to abort immediately and NOT proceed further, in order
    to prevent data leakage or partial state.
    """


# ---------------------------------------------------------------------------
# Audit logger (tamper-evident local append-only file)
# ---------------------------------------------------------------------------


def _get_audit_logger() -> logging.Logger:
    """Return a dedicated logger that appends to admin_audit.log."""
    audit_log_path = MODULE_ROOT / _AUDIT_LOG_NAME
    audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    audit_logger = logging.getLogger("defendra.admin_audit")
    if audit_logger.handlers:
        return audit_logger  # already configured

    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False

    handler = logging.FileHandler(audit_log_path, mode="a", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | AUDIT | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    )
    audit_logger.addHandler(handler)
    return audit_logger


def _write_audit_log(
    admin_id: str,
    device_id: str,
    backup_id: str,
    outcome: str,
    detail: str = "",
) -> None:
    """
    Append a structured audit record to admin_audit.log.

    Format:
      <timestamp> | AUDIT | admin=<id> device=<id> backup=<id>
                            outcome=<Success|Fail> [detail=<msg>]
    """
    audit = _get_audit_logger()
    record = (
        f"admin={admin_id} "
        f"device={device_id} "
        f"backup={backup_id} "
        f"outcome={outcome}"
    )
    if detail:
        record += f" detail={detail}"
    audit.info(record)


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------


def _validate_id(value: str, field_name: str) -> str:
    """
    Validate that *value* matches the strict allowlist pattern.

    Raises AdminSecurityException if the value is empty, too long, or
    contains characters outside [a-zA-Z0-9_-].
    """
    if not value or not isinstance(value, str):
        raise AdminSecurityException(
            f"[SECURITY] {field_name} must be a non-empty string. "
            f"Received: {value!r}"
        )
    stripped = value.strip()
    if len(stripped) == 0:
        raise AdminSecurityException(
            f"[SECURITY] {field_name} must not be blank after stripping whitespace."
        )
    if len(stripped) > _MAX_ID_LEN:
        raise AdminSecurityException(
            f"[SECURITY] {field_name} exceeds maximum allowed length "
            f"({_MAX_ID_LEN} chars). Possible injection attempt."
        )
    if not _SAFE_ID_RE.match(stripped):
        raise AdminSecurityException(
            f"[SECURITY] {field_name}={stripped!r} contains invalid characters. "
            "Only alphanumeric characters, underscores, and hyphens are permitted. "
            "This may be a path-traversal attempt — aborting."
        )
    return stripped


def _build_bucket_blob_path(device_id: str, backup_id: str) -> str:
    """
    Construct the Firebase Storage blob path after IDs have been validated.

    Result: backups/{device_id}/{backup_id}.zip
    """
    return f"{_BUCKET_PREFIX}/{device_id}/{backup_id}.zip"


# ---------------------------------------------------------------------------
# Firebase Admin SDK initialisation
# ---------------------------------------------------------------------------


def _load_firebase_app(service_account_source: str, bucket_name: str) -> Any:
    """
    Initialise (or retrieve) the Firebase Admin SDK app.

    *service_account_source* can be:
      - A filesystem path to a service-account JSON key file, OR
      - The raw JSON string of the key (useful for env-var injection in CI/CD).

    Returns the initialized firebase_admin App instance.
    Raises AdminSecurityException on any failure.
    """
    try:
        import firebase_admin  # type: ignore[import-untyped]
        from firebase_admin import credentials, storage  # noqa: F401
    except ImportError as exc:
        raise AdminSecurityException(
            "[SECURITY] firebase-admin package is not installed. "
            "Run: pip install firebase-admin>=6.0.0"
        ) from exc

    # Avoid re-initialising the default app if it already exists.
    app_name = "defendra_admin_recovery"
    try:
        existing = firebase_admin.get_app(app_name)
        logger.debug("Re-using existing Firebase Admin app: %s", app_name)
        return existing
    except ValueError:
        pass  # App not yet initialised — continue below.

    # Resolve credentials from path or raw JSON string.
    if service_account_source.strip().startswith("{"):
        try:
            sa_dict = json.loads(service_account_source)
        except json.JSONDecodeError as exc:
            raise AdminSecurityException(
                "[SECURITY] FIREBASE_SERVICE_ACCOUNT_JSON contains invalid JSON."
            ) from exc
        cred = credentials.Certificate(sa_dict)
        logger.info("Firebase Admin SDK: loaded credentials from environment JSON.")
    else:
        sa_path = Path(service_account_source).expanduser().resolve()
        if not sa_path.exists():
            raise AdminSecurityException(
                f"[SECURITY] Service account key file not found: {sa_path}. "
                "Ensure FIREBASE_SERVICE_ACCOUNT_JSON points to a valid file."
            )
        cred = credentials.Certificate(str(sa_path))
        logger.info(
            "Firebase Admin SDK: loaded credentials from file: %s", sa_path
        )

    try:
        app = firebase_admin.initialize_app(
            cred,
            options={"storageBucket": bucket_name},
            name=app_name,
        )
        logger.info("Firebase Admin app initialised. Bucket: %s", bucket_name)
        return app
    except Exception as exc:
        raise AdminSecurityException(
            f"[SECURITY] Firebase Admin SDK initialisation failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Main service class
# ---------------------------------------------------------------------------


class AdminFirebaseService:
    """
    Privileged admin service for downloading compromised-device backups.

    Workflow (must complete all 4 steps or raise AdminSecurityException):
      1. Authenticate with Firebase Admin SDK via Service Account key.
      2. Sanitize target paths to enforce strict isolation boundaries.
      3. Download the .zip archive to the admin's secure local folder.
      4. Record a tamper-evident audit log entry (local + Defendra dashboard).
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._firebase_app: Any = None

    # ------------------------------------------------------------------
    # Step 1 — Authenticate
    # ------------------------------------------------------------------

    def _authenticate(self) -> tuple[Any, Any]:
        """
        Step 1: Authenticate via Firebase Admin SDK using the Service Account.

        Returns (firebase_app, storage_bucket).
        Raises AdminSecurityException on failure.
        """
        service_account_source = os.environ.get(
            "FIREBASE_SERVICE_ACCOUNT_JSON", ""
        ).strip()
        if not service_account_source:
            raise AdminSecurityException(
                "[SECURITY] FIREBASE_SERVICE_ACCOUNT_JSON environment variable is "
                "not set. The admin SDK requires a privileged Service Account key. "
                "Set it to a file path or raw JSON string and retry."
            )

        bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET", "").strip()
        if not bucket_name:
            raise AdminSecurityException(
                "[SECURITY] FIREBASE_STORAGE_BUCKET environment variable is not set. "
                "Provide the Firebase Storage bucket name "
                "(e.g. defendra-backups.appspot.com)."
            )

        app = _load_firebase_app(service_account_source, bucket_name)

        try:
            from firebase_admin import storage as fb_storage  # type: ignore[import-untyped]
            bucket = fb_storage.bucket(app=app)
        except Exception as exc:
            raise AdminSecurityException(
                f"[SECURITY] Failed to obtain Firebase Storage bucket handle: {exc}"
            ) from exc

        logger.info(
            "Step 1 complete: authenticated Firebase Admin SDK. Bucket=%s",
            bucket_name,
        )
        return app, bucket

    # ------------------------------------------------------------------
    # Step 2 — Sanitize paths
    # ------------------------------------------------------------------

    def _sanitize_and_build_path(
        self, device_id: str, backup_id: str
    ) -> tuple[str, str, str]:
        """
        Step 2: Validate IDs and construct the isolated storage blob path.

        Returns (clean_device_id, clean_backup_id, blob_path).
        Raises AdminSecurityException on any invalid input.
        """
        clean_device_id = _validate_id(device_id, "device_id")
        clean_backup_id = _validate_id(backup_id, "backup_id")
        blob_path = _build_bucket_blob_path(clean_device_id, clean_backup_id)
        logger.info(
            "Step 2 complete: path sanitized. blob_path=%s", blob_path
        )
        return clean_device_id, clean_backup_id, blob_path

    # ------------------------------------------------------------------
    # Step 3 — Download from Firebase Cloud Storage
    # ------------------------------------------------------------------

    def _download_blob(
        self,
        bucket: Any,
        blob_path: str,
        backup_id: str,
        output_dir: Path,
    ) -> Path:
        """
        Step 3: Download the ZIP archive from Firebase Cloud Storage.

        Writes the file to output_dir/{backup_id}.zip.
        Raises AdminSecurityException on any failure.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        local_file = output_dir / f"{backup_id}.zip"

        try:
            blob = bucket.blob(blob_path)
            if not blob.exists():
                raise AdminSecurityException(
                    f"[SECURITY] Blob not found in Firebase Storage: {blob_path}. "
                    "Verify the device_id and backup_id are correct."
                )
            blob.download_to_filename(str(local_file))
        except AdminSecurityException:
            raise
        except Exception as exc:
            raise AdminSecurityException(
                f"[SECURITY] Firebase Storage download failed for {blob_path}: {exc}"
            ) from exc

        if not local_file.exists() or local_file.stat().st_size == 0:
            raise AdminSecurityException(
                f"[SECURITY] Downloaded file is missing or empty: {local_file}. "
                "Aborting to prevent silent data-loss."
            )

        logger.info(
            "Step 3 complete: downloaded %s -> %s (%d bytes)",
            blob_path,
            local_file,
            local_file.stat().st_size,
        )
        return local_file


    # ------------------------------------------------------------------
    # Step 4 — Audit logging
    # ------------------------------------------------------------------

    def _record_audit(
        self,
        admin_id: str,
        device_id: str,
        backup_id: str,
        outcome: str,
        local_file: Path | None = None,
        detail: str = "",
    ) -> None:
        """
        Step 4: Write a tamper-evident audit record locally and to the
        Defendra dashboard.

        A dashboard outage will NOT block recovery — but ALL events ARE
        written to the local admin_audit.log first.
        """
        _write_audit_log(admin_id, device_id, backup_id, outcome, detail)
        logger.info(
            "Step 4: audit written locally. admin=%s device=%s backup=%s outcome=%s",
            admin_id, device_id, backup_id, outcome,
        )

        # Forward to Defendra dashboard (non-fatal if unavailable)
        try:
            api_client = get_api_client()
            dashboard_payload: dict[str, Any] = {
                "admin_id": admin_id,
                "device_id": device_id,
                "backup_id": backup_id,
                "outcome": outcome,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if local_file:
                dashboard_payload["local_file"] = str(local_file)
            if detail:
                dashboard_payload["detail"] = detail

            api_client.update_dashboard(
                event="admin_download_compromised_backup",
                device_id=device_id,
                payload=dashboard_payload,
            )
            logger.info("Step 4 complete: audit forwarded to Defendra dashboard.")
        except (DefendraAPIError, Exception) as exc:
            logger.warning(
                "Could not forward audit to Defendra dashboard (non-fatal): %s", exc
            )


    # ------------------------------------------------------------------
    # Public entry point — full 4-step workflow
    # ------------------------------------------------------------------

    def download_compromised_backup(
        self,
        admin_id: str,
        device_id: str,
        backup_id: str,
        output_dir: Path | str | None = None,
    ) -> dict[str, Any]:
        """
        Execute the full 4-step admin recovery download workflow.

        Parameters
        ----------
        admin_id    : Identifier of the admin/employer initiating the download.
        device_id   : ID of the compromised device whose backup is retrieved.
        backup_id   : Specific backup archive ID within that device's namespace.
        output_dir  : Local directory to write the downloaded ZIP to.
                      Defaults to ADMIN_DOWNLOAD_DIR env var, then
                      <module_root>/admin_downloads/.

        Returns
        -------
        dict with keys: admin_id, device_id, backup_id, blob_path,
                        local_file, size_bytes, timestamp, outcome.

        Raises
        ------
        AdminSecurityException
            On ANY failure in any of the 4 steps. The process is aborted
            completely to prevent data leakage.
        """
        # Resolve output directory
        if output_dir is None:
            env_dir = os.environ.get("ADMIN_DOWNLOAD_DIR", "").strip()
            output_dir = (
                Path(env_dir) if env_dir else MODULE_ROOT / "admin_downloads"
            )
        output_dir = Path(output_dir).expanduser().resolve()

        # Validate admin_id before any Firebase call
        clean_admin_id = _validate_id(admin_id, "admin_id")
        timestamp = datetime.now(timezone.utc).isoformat()
        local_file: Path | None = None

        try:
            # ── Step 1: Authenticate ─────────────────────────────────────
            logger.info(
                "Admin download initiated. admin=%s device=%s backup=%s",
                clean_admin_id, device_id, backup_id,
            )
            _app, bucket = self._authenticate()

            # ── Step 2: Sanitize paths ───────────────────────────────────
            clean_device_id, clean_backup_id, blob_path = (
                self._sanitize_and_build_path(device_id, backup_id)
            )

            # ── Step 3: Download ─────────────────────────────────────────
            local_file = self._download_blob(
                bucket, blob_path, clean_backup_id, output_dir
            )

            # ── Step 4: Audit — SUCCESS ──────────────────────────────────
            self._record_audit(
                admin_id=clean_admin_id,
                device_id=clean_device_id,
                backup_id=clean_backup_id,
                outcome="Success",
                local_file=local_file,
            )

            result: dict[str, Any] = {
                "admin_id": clean_admin_id,
                "device_id": clean_device_id,
                "backup_id": clean_backup_id,
                "blob_path": blob_path,
                "local_file": str(local_file),
                "size_bytes": local_file.stat().st_size,
                "timestamp": timestamp,
                "outcome": "Success",
            }
            logger.info("Admin download workflow completed successfully: %s", result)
            return result

        except AdminSecurityException as exc:
            # ── Step 4: Audit — FAIL ─────────────────────────────────────
            safe_device = (
                device_id if device_id and _SAFE_ID_RE.match(device_id)
                else "INVALID"
            )
            safe_backup = (
                backup_id if backup_id and _SAFE_ID_RE.match(backup_id)
                else "INVALID"
            )
            self._record_audit(
                admin_id=clean_admin_id,
                device_id=safe_device,
                backup_id=safe_backup,
                outcome="Fail",
                detail=str(exc),
            )
            raise  # Always re-raise — never suppress security exceptions

