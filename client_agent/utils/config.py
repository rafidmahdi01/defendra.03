import json
import os
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv


def get_app_dir() -> Path:
    """Return the base directory where executable or main script resides."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    r"""
    Return the persistent writable data directory for logs, quarantine, and configs.
    Guarantees user-writable locations (%APPDATA%\Defendra, %LOCALAPPDATA%\Defendra)
    so the app never attempts to write into read-only Program Files.
    """
    candidates = []

    # 1. Custom env var if specified
    env_dir = os.getenv("DEFENDRA_DATA_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    # 2. Roaming AppData on Windows (%APPDATA%\Defendra) - standard for user configuration & state
    app_data = os.environ.get("APPDATA")
    if app_data:
        candidates.append(Path(app_data) / "Defendra")

    # 3. LocalAppData on Windows (%LOCALAPPDATA%\Defendra) - always user-writable
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Defendra")

    # 4. Windows ProgramData directory (standard enterprise shared data)
    program_data = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    candidates.append(Path(program_data) / "Defendra")

    # 5. User home directory
    candidates.append(Path.home() / ".defendra")

    # 6. Temp directory as final fallback
    candidates.append(Path(os.environ.get("TEMP", tempfile.gettempdir())) / "Defendra")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            # Test actual write permissions
            test_file = candidate / ".write_test"
            test_file.touch()
            test_file.unlink()
            return candidate
        except Exception:
            continue

    # Fallback to home dir or temp
    fallback = Path.home() / ".defendra"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    except Exception:
        return Path(tempfile.gettempdir()) / "Defendra"


def get_asset_path(filename: str) -> Path:
    """
    Locate bundled assets like icons (defendra_logo.ico).
    Handles PyInstaller one-file extraction (_MEIPASS) as well as direct dev paths.
    """
    # Check PyInstaller bundle temp dir
    if hasattr(sys, "_MEIPASS"):
        meipass_path = Path(sys._MEIPASS) / filename
        if meipass_path.exists():
            return meipass_path

    # Check executable / script directory
    app_path = get_app_dir() / filename
    if app_path.exists():
        return app_path

    # Check current working directory
    cwd_path = Path.cwd() / filename
    if cwd_path.exists():
        return cwd_path

    return app_path


def load_all_configs():
    """Load configuration from .env files, config.json, and system environment."""
    search_dirs = [
        get_app_dir(),
        get_data_dir(),
        Path(os.environ.get("APPDATA", "")) / "Defendra" if os.environ.get("APPDATA") else None,
        Path(os.environ.get("LOCALAPPDATA", "")) / "Defendra" if os.environ.get("LOCALAPPDATA") else None,
        Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "Defendra",
        Path.cwd()
    ]

    for d in search_dirs:
        if not d:
            continue
        env_file = d / ".env"
        if env_file.exists():
            try:
                load_dotenv(dotenv_path=env_file, override=False)
            except Exception:
                pass

        cfg_file = d / "config.json"
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if isinstance(cfg, dict):
                        for k, v in cfg.items():
                            env_key = k.upper()
                            if env_key not in os.environ and v is not None:
                                os.environ[env_key] = str(v)
                        # Map aliases
                        if "BACKEND_URL" in os.environ and "MARIA_API_URL" not in os.environ:
                            os.environ["MARIA_API_URL"] = os.environ["BACKEND_URL"]
                        if "ENROLLMENT_TOKEN" in os.environ and "MARIA_API_TOKEN" not in os.environ:
                            os.environ["MARIA_API_TOKEN"] = os.environ["ENROLLMENT_TOKEN"]
            except Exception:
                pass


# Execute config loading on module import
load_all_configs()
