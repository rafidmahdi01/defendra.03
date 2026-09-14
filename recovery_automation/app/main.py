"""
Recovery & Automation Module — standalone FastAPI application.

Runs on port 8001 by default and integrates with the existing Defendra backend
via HTTP (port 8000). Does NOT modify Defendra main.py or core routes.

Run from recovery_automation/:
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import (
    automation_router,
    backup_router,
    notification_router,
    recovery_router,
)
from app.services.scheduler import get_scheduler
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init scheduler from env defaults. Shutdown: stop scheduler."""
    settings = get_settings()
    logger.info(
        "Recovery & Automation starting on %s:%s",
        settings.recovery_host,
        settings.recovery_port,
    )
    logger.info("Defendra API target: %s", settings.defendra_api_url)

    # Auto-start scheduler if enabled in .env
    if settings.backup_schedule_enabled:
        get_scheduler().configure(
            enabled=True,
            interval_minutes=60,
            label="scheduled",
        )
        logger.info("Backup scheduler started from env config (interval=60m)")
    else:
        logger.info("Scheduled backups disabled (BACKUP_SCHEDULE_ENABLED=false)")

    yield

    get_scheduler().stop()
    logger.info("Recovery & Automation shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Defendra Recovery & Automation",
        description=(
            "Backup, recovery, automated incident response, and safe isolation simulation. "
            "Integrates with existing Defendra APIs without modifying core backend files."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register all route modules
    application.include_router(backup_router)
    application.include_router(recovery_router)
    application.include_router(automation_router)
    application.include_router(notification_router)

    @application.get("/health", tags=["Health"])
    def health() -> dict:
        return {
            "status": "ok",
            "module": "recovery_automation",
            "defendra_api": settings.defendra_api_url,
        }

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.recovery_host,
        port=s.recovery_port,
        reload=s.recovery_debug,
    )
