import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.api_core import exceptions as google_exceptions

from database.firebase import FirebaseConfigurationError
from utils.config import get_settings


logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(FirebaseConfigurationError)
    async def firebase_not_configured_handler(_request: Request, exc: FirebaseConfigurationError):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(google_exceptions.GoogleAPICallError)
    async def google_api_error_handler(request: Request, exc: google_exceptions.GoogleAPICallError):
        logger.exception("Firestore/Google API error on %s %s", request.method, request.url.path)
        settings = get_settings()
        detail = str(exc) if settings.environment == "development" else "Database request failed"
        return JSONResponse(status_code=503, content={"detail": detail})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        settings = get_settings()
        detail = f"{type(exc).__name__}: {exc}" if settings.debug else "Internal server error"
        return JSONResponse(status_code=500, content={"detail": detail})
