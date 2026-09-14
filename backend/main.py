from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.router import api_router
from database.firebase import get_firestore
from middleware.error_handler import register_error_handlers
from services.device_service import mark_stale_devices_offline
from utils.config import get_settings
from utils.logging import configure_logging
from websocket.dashboard import router as websocket_router


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Centralized cyber resilience monitoring, alerting, analytics, and offline sync API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router)
app.include_router(websocket_router)

# Serve the standalone frontend from the backend
_FRONTEND_DIR = Path(__file__).parent / "frontend"
_INDEX = _FRONTEND_DIR / "index.html"

if _INDEX.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(str(_INDEX))


@app.get("/health")
def health():
    # Fresh read on every request so .env edits and Sentinel flags match chat behavior.
    s = get_settings()
    configured = bool(
        (s.firebase_credentials_path or "").strip()
        or (s.firestore_emulator_host or "").strip()
    )
    huggingface_key = bool((s.huggingface_api_key or "").strip())
    return {
        "status": "ok",
        "environment": s.environment,
        "database": "firebase",
        "firebase_configured": configured,
        "sentinel_huggingface_llm": bool(s.huggingface_llm_enabled and huggingface_key),
        "huggingface_llm_enabled": s.huggingface_llm_enabled,
    }


@app.post("/api/system/offline-sweep")
def offline_sweep():
    db = get_firestore()
    count = mark_stale_devices_offline(db)
    return {"message": f"Marked {count} stale devices offline"}
