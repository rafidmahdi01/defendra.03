"""
Defendra.AI - Agent Build Script
Compiles the Defendra.AI Python Agent into a standalone, single-file Windows executable (DefendraAgent.exe).
Includes pywebview, pystray, and background scanner dependencies.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def main():
    root_dir = Path(__file__).resolve().parent
    os.chdir(root_dir)

    print("=" * 65)
    print("  Defendra.AI - Windows Agent Compilation")
    print("=" * 65)

    # 1. Verify required files
    main_script = root_dir / "main.py"
    icon_file = root_dir / "defendra_logo.ico"

    if not main_script.exists():
        print(f"[ERROR] Entry point not found: {main_script}")
        sys.exit(1)

    icon_arg = []
    data_arg = []

    if not icon_file.exists():
        print(f"[WARNING] Icon file not found: {icon_file}. Building without custom icon.")
    else:
        icon_arg = [f"--icon={icon_file}"]
        data_arg.append(f"--add-data={icon_file};.")

    # 1b. Locate and bundle the local UI dashboard folder (compiled React production files)
    local_ui_dir = root_dir / "local_ui"
    frontend_dist_dir = root_dir.parent / "frontend" / "dist"

    if not local_ui_dir.exists() and frontend_dist_dir.exists():
        print(f"[INFO] Copying compiled UI from {frontend_dist_dir} to {local_ui_dir}...")
        shutil.copytree(frontend_dist_dir, local_ui_dir, dirs_exist_ok=True)

    if local_ui_dir.exists() and (local_ui_dir / "index.html").exists():
        print(f"[INFO] Embedding local React UI: {local_ui_dir} -> local_ui/")
        data_arg.append(f"--add-data={local_ui_dir};local_ui")
    elif frontend_dist_dir.exists() and (frontend_dist_dir / "index.html").exists():
        print(f"[INFO] Embedding local React UI directly from frontend/dist: {frontend_dist_dir} -> local_ui/")
        data_arg.append(f"--add-data={frontend_dist_dir};local_ui")
    else:
        print("[WARNING] No compiled UI found in local_ui/ or frontend/dist! UI dashboard might be missing.")

    # 2. Verify / Install required build packages
    required_modules = {
        "PyInstaller": "pyinstaller",
        "webview": "pywebview",
        "bottle": "bottle",
        "pystray": "pystray",
        "PIL": "Pillow",
        "pythonnet": "pythonnet",
        "clr_loader": "clr_loader",
        "requests": "requests",
        "dotenv": "python-dotenv",
        "psutil": "psutil",
        "win32api": "pywin32",
    }

    print("[1/4] Checking build dependencies...")
    for mod_name, pip_name in required_modules.items():
        try:
            __import__(mod_name)
        except ImportError:
            print(f"      Installing missing dependency: {pip_name}...")
            subprocess.run([sys.executable, "-m", "pip", "install", pip_name], check=True)

    # 3. Clean up previous build directories
    print("[2/4] Cleaning previous build artifacts...")
    for folder in ["build", "dist", "__pycache__"]:
        path = root_dir / folder
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    spec_file = root_dir / "DefendraAgent.spec"
    if spec_file.exists():
        try:
            spec_file.unlink()
        except OSError:
            pass

    # 4. Construct PyInstaller command
    print("[3/4] Running PyInstaller build engine...")
    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--name=DefendraAgent",
        *icon_arg,
        *data_arg,
        "--collect-all=webview",
        "--collect-all=bottle",
        "--collect-all=pystray",
        "--collect-all=PIL",
        "--hidden-import=webview",
        "--hidden-import=webview.platforms.winforms",
        "--hidden-import=webview.platforms.edgechromium",
        "--hidden-import=webview.http",
        "--hidden-import=bottle",
        "--hidden-import=wsgiref",
        "--hidden-import=wsgiref.simple_server",
        "--hidden-import=wsgiref.handlers",
        "--hidden-import=socketserver",
        "--hidden-import=http.server",
        "--hidden-import=clr_loader",
        "--hidden-import=pythonnet",
        "--hidden-import=clr",
        "--hidden-import=pystray",
        "--hidden-import=pystray._win32",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.IcoImagePlugin",
        "--hidden-import=PIL.PngImagePlugin",
        "--hidden-import=win32api",
        "--hidden-import=win32file",
        "--hidden-import=win32con",
        "--hidden-import=win32gui",
        "--hidden-import=win32process",
        "--hidden-import=psutil",
        "--hidden-import=requests",
        "--hidden-import=dotenv",
        "--hidden-import=huggingface_hub",
        "--hidden-import=utils.config",
        "--hidden-import=utils.ai_analyzer",
        "--hidden-import=utils.alert_sender",
        "--hidden-import=utils.device_manager",
        "--hidden-import=utils.log_sender",
        "--hidden-import=behavior_monitor",
        "--hidden-import=email_scanner",
        "--hidden-import=system_scanner",
        "--hidden-import=usb_scanner",
        "--hidden-import=scan_config",
        str(main_script),
    ]

    start_time = time.time()
    result = subprocess.run(pyinstaller_args)

    if result.returncode != 0:
        print("[ERROR] PyInstaller compilation failed.")
        sys.exit(result.returncode)

    # 5. Move built executable to root directory
    dist_exe = root_dir / "dist" / "DefendraAgent.exe"
    target_exe = root_dir / "DefendraAgent.exe"

    if not dist_exe.exists():
        print(f"[ERROR] Built executable not found at: {dist_exe}")
        sys.exit(1)

    print("[4/4] Finalizing build and cleaning up...")
    if target_exe.exists():
        try:
            target_exe.unlink()
        except OSError:
            pass

    shutil.copy2(str(dist_exe), str(target_exe))

    # Clean up temporary build artifacts
    shutil.rmtree(root_dir / "build", ignore_errors=True)
    shutil.rmtree(root_dir / "dist", ignore_errors=True)
    if spec_file.exists():
        try:
            spec_file.unlink()
        except OSError:
            pass

    elapsed = round(time.time() - start_time, 2)
    exe_size_mb = round(target_exe.stat().st_size / (1024 * 1024), 2)

    print("=" * 65)
    print("  BUILD SUCCESSFUL!")
    print(f"  Target Binary : {target_exe}")
    print(f"  Size          : {exe_size_mb} MB")
    print(f"  Time Elapsed  : {elapsed}s")
    print("=" * 65)


if __name__ == "__main__":
    main()
