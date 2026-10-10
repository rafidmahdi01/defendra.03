"""
Firebase Cloud Storage client for backup archives.

Replaces legacy S3BackupClient to store backups securely in Firebase Cloud Storage.
"""

import os
from pathlib import Path
import firebase_admin
from firebase_admin import storage
from app.utils.logger import get_logger

logger = get_logger("firebase_storage")


class FirebaseBackupClient:
    """Upload and download backup objects using Firebase Cloud Storage."""

    def __init__(self) -> None:
        self._bucket = None

    @property
    def bucket_name(self) -> str | None:
        val = os.getenv("FIREBASE_STORAGE_BUCKET")
        if val:
            return val.removeprefix("gs://").strip()
        return None

    @property
    def enabled(self) -> bool:
        return bool(self.bucket_name)

    def _get_bucket(self):
        if self._bucket is not None:
            return self._bucket
        if not self.enabled:
            logger.info("Firebase Storage disabled or FIREBASE_STORAGE_BUCKET not set")
            return None
        try:
            # Pass bucket_name explicitly to storage.bucket
            self._bucket = storage.bucket(self.bucket_name)
            return self._bucket
        except Exception as exc:
            logger.error("Failed to access Firebase Storage bucket %s: %s", self.bucket_name, exc)
            return None

    def upload_backup(self, local_path: Path, backup_id: str) -> str | None:
        """Upload ZIP backup archive to Firebase Storage. Returns gs:// URI or None."""
        bucket = self._get_bucket()
        if not bucket:
            logger.info("Firebase Storage upload skipped (not configured)")
            return None

        blob_path = f"defendra-backups/{backup_id}.zip"
        try:
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(str(local_path))
            uri = f"gs://{self.bucket_name}/{blob_path}"
            logger.info("Uploaded backup %s to Firebase Storage: %s", backup_id, uri)
            return uri
        except Exception as exc:
            logger.error("Firebase Storage upload failed for %s: %s", backup_id, exc)
            return None

    def download_backup(self, backup_id: str, destination: Path) -> bool:
        """Download backup ZIP from Firebase Storage to local path."""
        bucket = self._get_bucket()
        if not bucket:
            logger.error("Firebase Storage download skipped (not configured)")
            return False

        blob_path = f"defendra-backups/{backup_id}.zip"
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            blob = bucket.blob(blob_path)
            blob.download_to_filename(str(destination))
            logger.info("Downloaded backup %s from Firebase Storage to %s", backup_id, destination)
            return True
        except Exception as exc:
            logger.error("Firebase Storage download failed for %s: %s", backup_id, exc)
            return False
