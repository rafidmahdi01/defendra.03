from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional
from google.cloud.firestore import Client

# Note: the existing project structure is assumed to have these modules
from auth.dependencies import require_admin, get_current_user
from database.firebase import get_firestore
from models.models import UserDoc
from utils.config import get_settings

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class IntegrationSettings(BaseModel):
    VIRUSTOTAL_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

class AgentKeysResponse(BaseModel):
    VIRUSTOTAL_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None

# Admin full access
@router.get("/integrations", response_model=IntegrationSettings)
def get_integrations(
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(require_admin),
):
    # Try fetching from environment .env first
    config = get_settings()
    env_keys = IntegrationSettings(
        VIRUSTOTAL_API_KEY=config.virustotal_api_key,
        HUGGINGFACE_API_KEY=config.huggingface_api_key,
        SMTP_PASSWORD=config.smtp_password,
    )
    
    # Merge with legacy Firestore if any environments are missing
    try:
        doc = db.collection("system_settings").document("integrations").get()
        if doc.exists:
            data = doc.to_dict() or {}
            env_keys.VIRUSTOTAL_API_KEY = env_keys.VIRUSTOTAL_API_KEY or data.get("VIRUSTOTAL_API_KEY")
            env_keys.HUGGINGFACE_API_KEY = env_keys.HUGGINGFACE_API_KEY or data.get("HUGGINGFACE_API_KEY")
            env_keys.SMTP_PASSWORD = env_keys.SMTP_PASSWORD or data.get("SMTP_PASSWORD")
    except Exception:
        pass
        
    return env_keys

@router.put("/integrations", response_model=IntegrationSettings)
def update_integrations(
    settings: IntegrationSettings,
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(require_admin),
):
    db.collection("system_settings").document("integrations").set(
        settings.model_dump(exclude_none=True), merge=True
    )
    return settings

# Endpoint agent access (returns only scanner keys)
@router.get("/agent-keys", response_model=AgentKeysResponse)
def get_agent_keys(
    db: Client = Depends(get_firestore),
    current_user: UserDoc = Depends(get_current_user),
):
    # Try fetching from environment .env first
    config = get_settings()
    keys = AgentKeysResponse(
        VIRUSTOTAL_API_KEY=config.virustotal_api_key,
        HUGGINGFACE_API_KEY=config.huggingface_api_key,
    )
    
    # Fallback to Firestore
    try:
        doc = db.collection("system_settings").document("integrations").get()
        if doc.exists:
            data = doc.to_dict() or {}
            keys.VIRUSTOTAL_API_KEY = keys.VIRUSTOTAL_API_KEY or data.get("VIRUSTOTAL_API_KEY")
            keys.HUGGINGFACE_API_KEY = keys.HUGGINGFACE_API_KEY or data.get("HUGGINGFACE_API_KEY")
    except Exception:
        pass

    return keys

