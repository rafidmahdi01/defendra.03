"""Auth module for recovery service."""

from app.auth.dependencies import CurrentUser, get_current_user, require_admin

__all__ = ["CurrentUser", "get_current_user", "require_admin"]
