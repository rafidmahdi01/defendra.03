"""
Defendra.AI - Enterprise Endpoint Protection Agent
Desktop Application with Native Dashboard UI, System Tray, and Autonomous Background Scanners.
"""

import logging
import os
import sys
import threading
from pathlib import Path
from PIL import Image
import pystray
import webview

# Ensure module imports resolve when packaged or executed directly
_CURRENT_DIR = Path(__file__).resolve().parent
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))

from utils.config import get_app_dir, get_data_dir, get_asset_path, load_all_configs
from behavior_monitor import run_behavior_monitor
from email_scanner import run_email_scanner
from system_scanner import run_system_scanner, run_full_scan
from usb_scanner import run_usb_scanner
from utils.device_manager import (
    register_or_get_device,
    run_heartbeat_loop,
    sync_email_scanner_settings,
)

# Initialize configuration
load_all_configs()

# Global state handles
window: webview.Window | None = None
tray_icon: pystray.Icon | None = None
is_exiting: bool = False
logger = logging.getLogger("DefendraAgent")


def get_webview_cache_dir() -> Path:
    r"""
    Return the dedicated user-writable cache folder for WebView2 runtime.
    Guarantees user-writable AppData location (%LOCALAPPDATA%\Defendra\WebView2Cache)
    so WebView2 never encounters Access Denied crashes when running from Program Files.
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        cache_dir = Path(local_app_data) / "Defendra" / "WebView2Cache"
    else:
        app_data = os.environ.get("APPDATA")
        if app_data:
            cache_dir = Path(app_data) / "Defendra" / "WebView2Cache"
        else:
            cache_dir = Path.home() / ".defendra" / "WebView2Cache"

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create WebView2 cache directory at {cache_dir}: {e}")
    return cache_dir


# Configure WebView2 user data folder early in process lifecycle
_webview_cache_path = get_webview_cache_dir()
os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(_webview_cache_path)
try:
    webview.settings["USER_DATA_DIR"] = str(_webview_cache_path)
except Exception:
    pass


def setup_logging():
    handlers = [logging.StreamHandler(sys.stdout)]

    candidate_dirs = [
        get_data_dir() / "logs",
        Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "Defendra" / "logs",
        Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "Defendra" / "logs",
        Path(os.environ.get("TEMP", ".")) / "Defendra" / "logs",
    ]

    for logs_dir in candidate_dirs:
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / "agent.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            handlers.append(file_handler)
            break
        except Exception:
            continue

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def ensure_directories():
    data_dir = get_data_dir()
    try:
        (data_dir / "logs").mkdir(parents=True, exist_ok=True)
        (data_dir / "quarantine").mkdir(parents=True, exist_ok=True)
        threats_log = data_dir / "logs" / "threats.log"
        if not threats_log.exists():
            threats_log.touch()
    except OSError as e:
        logger.warning(f"Failed to ensure data directories in {data_dir}: {e}")

def resolve_ui_target() -> str:
    """
    Resolve the local dashboard UI path.
    Prioritizes embedded local UI files (index.html) from PyInstaller's sys._MEIPASS,
    the application folder, or development workspace.
    Completely decouples the UI display from external network availability.
    """
    # 1. Developer CLI overrides (--url or --dashboard-url) for local dev/testing
    for i, arg in enumerate(sys.argv):
        if arg in ("--url", "--dashboard-url") and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if arg.startswith("--url="):
            return arg.split("=", 1)[1]
        if arg.startswith("--dashboard-url="):
            return arg.split("=", 1)[1]

    # 2. Search candidate locations for the bundled local React dashboard
    candidate_paths = []

    # Case A: PyInstaller single-file temporary extraction directory (_MEIPASS)
    if hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidate_paths.extend([
            meipass / "local_ui" / "index.html",
            meipass / "dist" / "index.html",
            meipass / "index.html",
        ])

    # Case B: Application root directory (installed location or standalone folder)
    app_dir = get_app_dir()
    candidate_paths.extend([
        app_dir / "local_ui" / "index.html",
        app_dir / "dist" / "index.html",
        app_dir / "frontend" / "dist" / "index.html",
    ])

    # Case C: Script directory & relative dev paths
    script_dir = Path(__file__).resolve().parent
    candidate_paths.extend([
        script_dir / "local_ui" / "index.html",
        script_dir / "dist" / "index.html",
        script_dir.parent / "frontend" / "dist" / "index.html",
        script_dir.parent / "dist" / "index.html",
        Path.cwd() / "local_ui" / "index.html",
        Path.cwd() / "dist" / "index.html",
    ])

    for p in candidate_paths:
        if p.is_file():
            resolved = str(p.resolve())
            logger.info(f"Loaded embedded local UI dashboard from: {resolved}")
            return resolved

    # Case D: Check explicit dev UI environment variable if actively developing
    for env_var in ("DEFENDRA_UI_URL", "FRONTEND_DEV_URL"):
        val = os.getenv(env_var)
        if val and val.strip():
            logger.info(f"Using development UI URL from {env_var}: {val.strip()}")
            return val.strip()

    # Fallback to local_ui path
    default_path = str((get_app_dir() / "local_ui" / "index.html").resolve())
    logger.warning(f"Local UI bundle not found in candidate paths. Falling back to: {default_path}")
    return default_path

def show_dashboard(icon=None, item=None):
    """Restore and show the native webview dashboard window."""
    global window
    if window:
        try:
            window.show()
            window.restore()
        except Exception as e:
            logger.error(f"Error showing dashboard window: {e}")


def trigger_manual_scan(icon=None, item=None):
    """Trigger an on-demand full system scan from the system tray."""
    threading.Thread(target=run_full_scan, daemon=True, name="manual-system-scan").start()
    if tray_icon:
        try:
            tray_icon.notify("System scan initiated in background.", "Defendra.AI Scanner")
        except Exception:
            pass


def exit_application(icon=None, item=None):
    """Cleanly stop background components and exit the application."""
    global is_exiting, tray_icon, window
    is_exiting = True
    logger.info("Exiting Defendra.AI Agent...")

    if tray_icon:
        try:
            tray_icon.stop()
        except Exception:
            pass

    if window:
        try:
            window.destroy()
        except Exception:
            pass

    os._exit(0)


def on_window_closing():
    """
    Prevent the application from terminating when the user closes the dashboard window.
    Hides the window to the system tray so background monitoring stays alive.
    """
    global is_exiting, window, tray_icon
    if not is_exiting:
        if window:
            window.hide()
        if tray_icon:
            try:
                tray_icon.notify(
                    "Defendra.AI is running in the background to protect your endpoint.",
                    "Defendra.AI Active"
                )
            except Exception:
                pass
        return False  # Suppress window destruction
    return True


def create_tray_icon(icon_path: Path) -> pystray.Icon:
    """Create and configure the system tray icon."""
    try:
        icon_image = Image.open(str(icon_path))
    except Exception:
        # Fallback 64x64 icon with Defendra teal branding
        icon_image = Image.new("RGB", (64, 64), color=(20, 184, 166))

    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", show_dashboard, default=True),
        pystray.MenuItem("Protection: Active", None, enabled=False),
        pystray.MenuItem("Run System Scan", trigger_manual_scan),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit Defendra.AI", exit_application),
    )

    return pystray.Icon(
        name="DefendraAgent",
        icon=icon_image,
        title="Defendra.AI - Endpoint Protection",
        menu=menu,
    )


def start_background_monitors():
    """Start all autonomous background scanners in dedicated daemon threads."""
    device_id = register_or_get_device()
    if device_id:
        logger.info(f"Connected to Defendra backend as device_id={device_id}")
    else:
        logger.warning("Could not register with backend. Operating in autonomous local mode.")

    sync_email_scanner_settings()

    threads = [
        threading.Thread(target=run_email_scanner, daemon=True, name="email-scanner"),
        threading.Thread(target=run_usb_scanner, daemon=True, name="usb-scanner"),
        threading.Thread(target=run_behavior_monitor, daemon=True, name="behavior-monitor"),
        threading.Thread(target=run_heartbeat_loop, daemon=True, name="heartbeat"),
        threading.Thread(target=run_system_scanner, daemon=True, name="system-scanner"),
    ]

    for t in threads:
        t.start()
        logger.info(f"Started scanner thread: {t.name}")


def main():
    global window, tray_icon

    setup_logging()
    ensure_directories()

    logger.info("============================================================")
    logger.info("Defendra.AI - Enterprise Endpoint Protection Agent")
    logger.info("============================================================")

    # 1. Start background security monitoring threads
    start_background_monitors()

    # 2. Locate application icon
    icon_path = get_asset_path("defendra_logo.ico")

    # 3. Setup System Tray icon
    tray_icon = create_tray_icon(icon_path)
    tray_icon.run_detached()

    # 4. Resolve local UI target and create native pywebview window
    ui_target = resolve_ui_target()
    logger.info(f"Opening native local dashboard UI: {ui_target}")

    window = webview.create_window(
        title="Defendra.AI - Enterprise Endpoint Protection",
        url=ui_target,
        width=1280,
        height=800,
        min_size=(900, 600),
        confirm_close=False,
    )

    # Hook close event to minimize to tray instead of quitting
    window.events.closing += on_window_closing

    # 5. Start pywebview GUI main loop with embedded HTTP server and explicit storage_path in AppData
    webview_cache_dir = get_webview_cache_dir()
    logger.info(f"Using WebView2 cache directory: {webview_cache_dir}")

    webview.start(
        icon=str(icon_path) if icon_path.exists() else None,
        http_server=True,
        debug=False,
        private_mode=False,
        storage_path=str(webview_cache_dir),
    )


if __name__ == "__main__":
    main()
