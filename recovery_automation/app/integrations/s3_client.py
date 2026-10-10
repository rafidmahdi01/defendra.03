"""
Legacy S3 client alias module for backward compatibility.
Redirects S3BackupClient to FirebaseBackupClient.
"""

from app.integrations.firebase_storage import FirebaseBackupClient as S3BackupClient  # noqa: F401

__all__ = ["S3BackupClient"]

