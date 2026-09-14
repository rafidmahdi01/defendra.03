"""
Optional AWS S3 upload for backup archives.

Gracefully no-ops when S3 is disabled or boto3 credentials are missing.
"""

from pathlib import Path

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("s3_client")


class S3BackupClient:
    """Upload and list backup objects in S3."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    @property
    def enabled(self) -> bool:
        return (
            self.settings.s3_upload_enabled
            and bool(self.settings.s3_bucket)
            and bool(self.settings.aws_access_key_id)
        )

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.enabled:
            return None
        try:
            import boto3

            self._client = boto3.client(
                "s3",
                region_name=self.settings.aws_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
            )
            return self._client
        except ImportError:
            logger.error("boto3 not installed; S3 upload skipped")
            return None

    def upload_backup(self, local_path: Path, backup_id: str) -> str | None:
        """Upload ZIP to S3. Returns s3:// URI or None."""
        client = self._get_client()
        if not client:
            logger.info("S3 upload disabled or not configured")
            return None

        key = f"{self.settings.s3_prefix.rstrip('/')}/{backup_id}.zip"
        try:
            client.upload_file(str(local_path), self.settings.s3_bucket, key)
            uri = f"s3://{self.settings.s3_bucket}/{key}"
            logger.info("Uploaded backup to %s", uri)
            return uri
        except Exception as exc:
            logger.error("S3 upload failed for %s: %s", backup_id, exc)
            return None

    def download_backup(self, backup_id: str, destination: Path) -> bool:
        """Download backup ZIP from S3 to local path."""
        client = self._get_client()
        if not client:
            return False
        key = f"{self.settings.s3_prefix.rstrip('/')}/{backup_id}.zip"
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(self.settings.s3_bucket, key, str(destination))
            return True
        except Exception as exc:
            logger.error("S3 download failed for %s: %s", backup_id, exc)
            return False
