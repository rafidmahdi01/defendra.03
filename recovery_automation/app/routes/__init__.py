from app.routes.automation_routes import router as automation_router
from app.routes.backup_routes import router as backup_router
from app.routes.notification_routes import router as notification_router
from app.routes.recovery_routes import router as recovery_router

__all__ = [
    "automation_router",
    "backup_router",
    "notification_router",
    "recovery_router",
]
