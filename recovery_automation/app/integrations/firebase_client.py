"""
Firebase Storage Client — User-facing backup uploads.

This client is used by BackupService to upload device backups to Firebase
Storage, making them available for admin compromise-recovery operations.

Separate from AdminFirebaseService, which uses Firebase Admin SDK to *download*
backups with elevated privileges.

Storage schema: backups/{device_id}/{backup_id}.zip
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("firebase_client")


class FirebaseStorageClient:
    """Upload device backups to Firebase Cloud Storage."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._firebase_app: Any = None
        self._bucket: Any = None

    @property
    def enabled(self) -> bool:
        """Check if Firebase credentials are configured."""
        sa_json = self.settings.firebase_service_account_json.strip()
        bucket = self.settings.firebase_storage_bucket.removeprefix("gs://").strip()
        return bool(sa_json) and bool(bucket)

    def _get_bucket(self) -> Any:
        """Initialize Firebase Admin SDK and return bucket handle."""
        if self._bucket is not None:
            return self._bucket

        if not self.enabled:
            return None

        try:
            import firebase_admin  # type: ignore[import-untyped]
            from firebase_admin import credentials, storage  # type: ignore[import-untyped]
        except ImportError:
            logger.error("firebase-admin not installed; Firebase upload disabled")
            return None

        # Avoid re-initializing if app already exists
        app_name = "defendra_user_backups"
        try:
            existing_app = firebase_admin.get_app(app_name)
            logger.debug("Re-using existing Firebase app: %s", app_name)
            self._firebase_app = existing_app
        except ValueError:
            # Initialize new app
            service_account_source = self.settings.firebase_service_account_json.strip()
            bucket_name = self.settings.firebase_storage_bucket.removeprefix("gs://").strip()

            # Load credentials from file or raw JSON
            if service_account_source.startswith("{"):
                import json
                try:
                    sa_dict = json.loads(service_account_source)
                    cred = credentials.Certificate(sa_dict)
                    logger.info("Firebase: loaded credentials from environment JSON")
                except json.JSONDecodeError as e:
                    logger.error("Firebase: invalid JSON: %s", e)
                    return None
            else:
                sa_path = Path(service_account_source).expanduser().resolve()
                if not sa_path.exists():
                    logger.error("Firebase: service account key not found: %s", sa_path)
                    return None
                cred = credentials.Certificate(str(sa_path))
                logger.info("Firebase: loaded credentials from file: %s", sa_path)

            try:
                self._firebase_app = firebase_admin.initialize_app(
                    cred,
                    options={"storageBucket": bucket_name},
                    name=app_name,
                )
                logger.info("Firebase app initialized. Bucket: %s", bucket_name)
            except Exception as e:
                logger.error("Firebase initialization failed: %s", e)
                return None

        try:
            from firebase_admin import storage as fb_storage  # type: ignore[import-untyped]
            self._bucket = fb_storage.bucket(app=self._firebase_app)
            return self._bucket
        except Exception as e:
            logger.error("Failed to get Firebase Storage bucket: %s", e)
            return None


    def upload_backup(
        self,
        local_path: Path,
        device_id: str,
        backup_id: str,
    ) -> str | None:
        """
        Upload backup ZIP to Firebase Storage.

        Storage path: backups/{device_id}/{backup_id}.zip

        Returns Firebase Storage gs:// URI on success, None on failure.
        """
        bucket = self._get_bucket()
        if not bucket:
            logger.info("Firebase upload disabled or not configured")
            return None

        if not device_id or not backup_id:
            logger.warning("Cannot upload to Firebase: device_id or backup_id is empty")
            return None

        blob_path = f"backups/{device_id}/{backup_id}.zip"

        try:
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(str(local_path))
            uri = f"gs://{bucket.name}/{blob_path}"
            logger.info("Uploaded backup to Firebase: %s", uri)
            return uri
        except Exception as e:
            logger.error("Firebase upload failed for %s: %s", blob_path, e)
            return None

    def download_backup(
        self,
        device_id: str,
        backup_id: str,
        destination: Path,
    ) -> bool:
        """
        Download backup ZIP from Firebase Storage to local path.

        Storage path: backups/{device_id}/{backup_id}.zip
        """
        bucket = self._get_bucket()
        if not bucket:
            return False

        blob_path = f"backups/{device_id}/{backup_id}.zip"

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            blob = bucket.blob(blob_path)
            if not blob.exists():
                logger.error("Firebase blob not found: %s", blob_path)
                return False
            blob.download_to_filename(str(destination))
            logger.info("Downloaded backup from Firebase: %s -> %s", blob_path, destination)
            return True
        except Exception as e:
            logger.error("Firebase download failed for %s: %s", blob_path, e)
            return False

    def list_device_backups(self, device_id: str) -> list[str]:
        """
        List all backup IDs for a specific device in Firebase Storage.

        Returns list of backup_ids (without .zip extension).
        """
        bucket = self._get_bucket()
        if not bucket:
            return []

        prefix = f"backups/{device_id}/"

        try:
            blobs = bucket.list_blobs(prefix=prefix)
            backup_ids = []
            for blob in blobs:
                # Extract backup_id from path: backups/{device_id}/{backup_id}.zip
                name = blob.name
                if name.endswith(".zip"):
                    backup_id = name.split("/")[-1][:-4]  # Remove .zip
                    backup_ids.append(backup_id)
            logger.info("Found %d Firebase backups for device %s", len(backup_ids), device_id)
            return backup_ids
        except Exception as e:
            logger.error("Failed to list Firebase backups for %s: %s", device_id, e)
            return []
