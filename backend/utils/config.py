import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve `.env` from the backend package root so Firebase/JWT load correctly even when
# uvicorn's cwd is not `backend/` (common when launching from IDEs or process managers).
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_ENV = _BACKEND_DIR.parent / ".env"
_BACKEND_ENV = _BACKEND_DIR / ".env"
_CLIENT_AGENT_ENV = _BACKEND_DIR.parent / "client_agent" / ".env"

# Explicitly load .env files into os.environ for os.getenv compatibility
if _ROOT_ENV.is_file():
    load_dotenv(dotenv_path=_ROOT_ENV)
if _BACKEND_ENV.is_file():
    load_dotenv(dotenv_path=_BACKEND_ENV)

_ENV_FILES: tuple[str, ...] = (
    str(_ROOT_ENV),
    str(_BACKEND_ENV),
    *(
        (str(_CLIENT_AGENT_ENV.resolve()),)
        if _CLIENT_AGENT_ENV.is_file()
        else ()
    ),
)


class Settings(BaseSettings):
    app_name: str = "Defendra.AI"
    environment: str = "development"
    debug: bool = False

    # Firebase — use either a service account JSON **or** the local Firestore emulator.
    firebase_credentials_path: str = Field(
        default="",
        description="Absolute path to the Firebase service account JSON key file.",
    )
    firebase_credentials_json: str = Field(
        default="",
        description="Base64-encoded Firebase service account JSON (alternative to file path).",
    )
    firestore_emulator_host: str = Field(
        default="",
        description='Local emulator, e.g. "127.0.0.1:8080". Sets FIRESTORE_EMULATOR_HOST for firebase-admin.',
    )
    firebase_project_id: str = Field(
        default="defendraai",
        description="GCP project id (required for emulator; can match your Firebase project in production).",
    )

    @field_validator("firebase_credentials_path", mode="after")
    @classmethod
    def strip_cred_path(cls, v: str) -> str:
        if not v:
            return ""
        return v.strip().strip('"').strip("'")

    @field_validator("firestore_emulator_host", mode="after")
    @classmethod
    def strip_emulator_host(cls, v: str) -> str:
        if not v:
            return ""
        return v.strip().strip('"').strip("'")

    # Strictly required JWT Secret Key from .env
    fastapi_jwt_secret: str = Field(
        ...,
        alias="FASTAPI_JWT_SECRET",
        description="Mandatory JWT secret key loaded from .env. Crashes server startup if missing.",
    )

    @field_validator("fastapi_jwt_secret", mode="after")
    @classmethod
    def validate_fastapi_jwt_secret(cls, v: str) -> str:
        secret = (v or "").strip().strip('"').strip("'")
        if not secret:
            secret = (os.getenv("FASTAPI_JWT_SECRET") or "").strip().strip('"').strip("'")
        if not secret:
            raise ValueError(
                "FASTAPI_JWT_SECRET is missing or empty in .env. "
                "The FastAPI server strictly requires a 32-character random string configured "
                "for FASTAPI_JWT_SECRET in your .env file to boot."
            )
        return secret

    @property
    def jwt_secret_key(self) -> str:
        """Alias property to maintain compatibility with auth security modules."""
        return self.fastapi_jwt_secret

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    heartbeat_timeout_seconds: int = 120
    log_export_limit: int = 10000

    # SendGrid SMTP Configuration — hardcoded defaults with SMTP_PASSWORD loaded from .env
    smtp_host: str = Field(
        default="smtp.sendgrid.net",
        alias="SMTP_HOST",
        description="Hardcoded SendGrid SMTP host",
    )
    smtp_port: int = Field(
        default=587,
        alias="SMTP_PORT",
        description="Hardcoded SendGrid SMTP TLS port",
    )
    smtp_user: str = Field(
        default="apikey",
        alias="SMTP_USER",
        description="Hardcoded SendGrid SMTP username",
    )
    smtp_password: str = Field(
        default="",
        alias="SMTP_PASSWORD",
        description="SendGrid SMTP API key loaded directly from .env",
    )
    notification_from_email: str = Field(
        default="ceo@technohavenmalaysia.com",
        alias="NOTIFICATION_FROM_EMAIL",
        description="SendGrid verified sender email",
    )

    # API Keys loaded directly from .env
    virustotal_api_key: str = Field(
        default="",
        alias="VIRUSTOTAL_API_KEY",
        description="VirusTotal API key loaded directly from .env",
    )
    huggingface_api_key: str = Field(
        default="",
        alias="HUGGINGFACE_API_KEY",
        description="Access token from https://huggingface.co/settings/tokens loaded directly from .env",
    )
    huggingface_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct",
        description="Hugging Face chat model id.",
    )
    huggingface_provider: str = Field(
        default="featherless-ai",
        description="Hugging Face Inference Provider for the selected model.",
    )
    huggingface_llm_enabled: bool = Field(
        default=True,
        description="If false or no token is configured, Sentinel uses the Firestore snapshot.",
    )

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    # Compatibility properties for uppercase access
    @property
    def SMTP_PASSWORD(self) -> str:
        return self.smtp_password

    @property
    def VIRUSTOTAL_API_KEY(self) -> str:
        return self.virustotal_api_key

    @property
    def HUGGINGFACE_API_KEY(self) -> str:
        return self.huggingface_api_key

    @property
    def FASTAPI_JWT_SECRET(self) -> str:
        return self.fastapi_jwt_secret


def get_settings() -> Settings:
    return Settings()
