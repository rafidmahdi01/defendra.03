import base64
import json
import logging
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

from utils.config import get_settings

logger = logging.getLogger(__name__)

_initialized = False


class FirebaseConfigurationError(Exception):
    """Raised when Firestore is used but neither emulator nor service account is configured."""


def init_firebase() -> None:
    global _initialized
    if _initialized or firebase_admin._apps:
        _initialized = True
        return

    settings = get_settings()
    emulator = settings.firestore_emulator_host
    cred_path = settings.firebase_credentials_path
    cred_json_b64 = settings.firebase_credentials_json
    project_id = settings.firebase_project_id or "defendraai"

    # Route traffic to emulator when configured, or ensure no stale env var
    # bleeds into cloud mode (an empty FIRESTORE_EMULATOR_HOST causes dns:/// crash).
    if emulator:
        os.environ["FIRESTORE_EMULATOR_HOST"] = emulator
        logger.info("Firestore emulator configured at %s", emulator)
    else:
        os.environ.pop("FIRESTORE_EMULATOR_HOST", None)

    if cred_json_b64:
        # Decode base64 JSON credentials stored in env var (no file path needed)
        try:
            cred_dict = json.loads(base64.b64decode(cred_json_b64).decode("utf-8"))
        except Exception as exc:
            raise ValueError(
                "FIREBASE_CREDENTIALS_JSON is set but could not be decoded. "
                "Ensure it is a valid base64-encoded service account JSON."
            ) from exc
        cred = credentials.Certificate(cred_dict)
        try:
            firebase_admin.initialize_app(cred, options={"projectId": project_id} if project_id else {})
            logger.info("Firebase Admin initialized with inline credentials (project=%s)", project_id)
        except ValueError:
            logger.info("Firebase Admin already initialized")
    elif cred_path:
        placeholder_values = {
            "C:\\path\\to\\serviceAccount.json",
            "C:/path/to/serviceAccount.json",
            "/path/to/serviceAccount.json",
            "path/to/serviceAccount.json",
        }
        if cred_path.strip() in placeholder_values:
            raise FirebaseConfigurationError(
                "Firebase credentials path in backend/.env is still the example placeholder. "
                "Set FIREBASE_CREDENTIALS_PATH to your service account JSON file or set "
                "FIRESTORE_EMULATOR_HOST for local emulator usage."
            )

        path = Path(cred_path).expanduser()
        # Resolve relative paths against the backend directory (where this file lives)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent.parent / path
        if not path.is_file():
            raise FileNotFoundError(
                f"Firebase credentials file not found: {path}. "
                "Set FIREBASE_CREDENTIALS_PATH in backend/.env to your service account JSON."
            )
        cred = credentials.Certificate(str(path.resolve()))
        try:
            firebase_admin.initialize_app(cred, options={"projectId": project_id} if project_id else {})
            mode = f"emulator at {emulator}" if emulator else "cloud Firestore"
            logger.info("Firebase Admin initialized with service account -> %s", mode)
        except ValueError:
            logger.info("Firebase Admin already initialized")
    elif emulator:
        # Emulator-only mode: no credentials needed, Firebase Admin accepts a project-id-only init.
        try:
            firebase_admin.initialize_app(options={"projectId": project_id})
            logger.info("Firebase Admin using Firestore emulator at %s (project=%s)", emulator, project_id)
        except ValueError:
            logger.info("Firebase Admin already initialized (emulator)")
    else:
        raise FirebaseConfigurationError(
            "Firebase is not configured. In backend/.env set FIREBASE_CREDENTIALS_PATH to your "
            "Firebase service account JSON file (Firebase Console → Project settings → Service accounts → "
            "Generate new private key). Enable Cloud Firestore in that project. "
            "Then restart the API. Example: FIREBASE_CREDENTIALS_PATH=C:/Users/You/Downloads/myapp-firebase-adminsdk.json"
        )

    _initialized = True


def get_firestore() -> Client:
    """
    Return the Firestore client, initializing Firebase on first use.

    When using the emulator, use google.cloud.firestore.Client directly so we do not
    require Application Default Credentials (firebase_admin.firestore.client() can
    still call google.auth.default() on some SDK versions).
    """
    init_firebase()
    settings = get_settings()
    emulator = (settings.firestore_emulator_host or "").strip()
    project_id = settings.firebase_project_id or "defendraai"
    if emulator:
        os.environ["FIRESTORE_EMULATOR_HOST"] = emulator
        from google.cloud import firestore as gc_firestore

        return gc_firestore.Client(project=project_id)
    return firestore.client()
