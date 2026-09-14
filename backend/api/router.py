from fastapi import APIRouter

from routes import alerts, analytics, auth, devices, logs, sentinel_chat, sync, whitelist


api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(devices.router)
api_router.include_router(logs.router)
api_router.include_router(alerts.router)
api_router.include_router(analytics.router)
api_router.include_router(sentinel_chat.router)
api_router.include_router(sync.router)
api_router.include_router(whitelist.router)
