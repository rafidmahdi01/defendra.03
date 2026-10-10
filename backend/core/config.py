"""
Defendra.AI Core Configuration Re-export
Provides backward and alternate module path compatibility for backend/core/config.py
"""
from utils.config import (
    Settings,
    get_settings,
    _BACKEND_DIR,
    _ROOT_ENV,
    _ENV_FILES,
)

__all__ = ["Settings", "get_settings", "_BACKEND_DIR", "_ROOT_ENV", "_ENV_FILES"]
