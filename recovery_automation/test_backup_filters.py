"""Unit tests for enterprise backup filters in backup_service.py."""

import sys
import tempfile
from pathlib import Path

# Add recovery_automation app to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.backup_service import (
    BLOCKED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    BackupService,
    is_excluded_directory,
    should_include_file,
)


def test_constants():
    """Verify enterprise filter constants."""
    print("Testing enterprise filter constants...")
    assert MAX_FILE_SIZE_MB == 50, f"Expected MAX_FILE_SIZE_MB = 50, got {MAX_FILE_SIZE_MB}"
    assert MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024, "MAX_FILE_SIZE_BYTES calculation mismatch"

    required_blocked = {".mp4", ".iso", ".exe", ".ost", ".tmp"}
    for ext in required_blocked:
        assert ext in BLOCKED_EXTENSIONS, f"Extension {ext} missing from BLOCKED_EXTENSIONS"
    print("  ✓ Constants defined correctly.")


def test_directory_exclusion():
    """Verify system directory and AppData exclusions."""
    print("Testing directory exclusion logic...")

    excluded_paths = [
        Path("C:/Windows/System32"),
        Path("C:/Program Files/Defendra"),
        Path("C:/Program Files (x86)/App"),
        Path("C:/ProgramData/Defendra"),
        Path("C:/Users/TestUser/AppData/Local/Temp"),
        Path("C:/Users/TestUser/AppData/Roaming/App"),
        Path("C:/Users/TestUser/.git/objects"),
        Path("C:/Users/TestUser/.cache"),
        Path("/proc/sys"),
        Path("/dev"),
    ]

    allowed_paths = [
        Path("C:/Users/TestUser/Documents"),
        Path("C:/Users/TestUser/Desktop"),
        Path("C:/Users/TestUser/Downloads"),
        Path("C:/Users/TestUser/Pictures"),
        Path("./data/important"),
    ]

    for p in excluded_paths:
        assert is_excluded_directory(p) is True, f"Path should be excluded: {p}"

    for p in allowed_paths:
        assert is_excluded_directory(p) is False, f"Path should be allowed: {p}"

    print("  ✓ Directory exclusion tests passed.")


def test_file_filtering():
    """Verify extension and file size limit checks."""
    print("Testing file filtering logic...")

    module_root = Path(__file__).parent
    scratch_dir = module_root / "test_filter_scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Allowed file
        allowed_file = scratch_dir / "valid_doc.pdf"
        allowed_file.write_text("Test content", encoding="utf-8")
        assert should_include_file(allowed_file) is True

        # 2. Blocked extension (.exe, .mp4, .tmp, .ost, .iso)
        exe_file = scratch_dir / "installer.exe"
        exe_file.write_text("binary", encoding="utf-8")
        assert should_include_file(exe_file) is False

        mp4_file = scratch_dir / "video.mp4"
        mp4_file.write_text("video stream", encoding="utf-8")
        assert should_include_file(mp4_file) is False

        ost_file = scratch_dir / "outlook.ost"
        ost_file.write_text("outlook data", encoding="utf-8")
        assert should_include_file(ost_file) is False

        # 3. Oversized file (> 50MB)
        large_file = scratch_dir / "large_dataset.dat"
        # Create a sparse file of 51MB
        with open(large_file, "wb") as f:
            f.seek(51 * 1024 * 1024 - 1)
            f.write(b"\0")
        assert should_include_file(large_file) is False

    finally:
        import shutil
        shutil.rmtree(scratch_dir, ignore_errors=True)

    print("  ✓ File filtering tests passed.")


def test_create_backup_integration():
    """Verify create_backup with filtered directory structure."""
    print("Testing BackupService.create_backup integration...")

    module_root = Path(__file__).parent
    scratch_dir = module_root / "test_backup_scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc_dir = scratch_dir / "Documents"
        doc_dir.mkdir()

        # Files in Documents
        valid_doc = doc_dir / "report.docx"
        valid_doc.write_text("Report content", encoding="utf-8")

        blocked_video = doc_dir / "presentation.mp4"
        blocked_video.write_text("Media content", encoding="utf-8")

        blocked_exe = doc_dir / "tool.exe"
        blocked_exe.write_text("Executable content", encoding="utf-8")

        # Excluded subfolder (e.g. AppData inside test tree)
        appdata_dir = doc_dir / "AppData" / "Local"
        appdata_dir.mkdir(parents=True)
        appdata_file = appdata_dir / "cache.json"
        appdata_file.write_text("{}", encoding="utf-8")

        service = BackupService()
        meta = service.create_backup(
            paths=[str(doc_dir)],
            label="filter_test",
            device_id="test-filter-device",
        )

        assert meta["file_count"] == 1, f"Expected 1 file archived, got {meta['file_count']}"
        print(f"  ✓ Backup created successfully. Archived files count: {meta['file_count']}")

    finally:
        import shutil
        shutil.rmtree(scratch_dir, ignore_errors=True)


if __name__ == "__main__":
    test_constants()
    test_directory_exclusion()
    test_file_filtering()
    test_create_backup_integration()
    print("\n🎉 ALL BACKUP FILTER TESTS PASSED!")
