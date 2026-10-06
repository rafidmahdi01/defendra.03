"""Quick test to verify device_id auto-detection from hostname."""

import platform
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.backup_service import BackupService


def test_device_autodetect():
    """Test that device_id is auto-detected when not provided."""
    service = BackupService()
    
    # Test 1: No device_id provided (should auto-detect)
    detected_id = service._get_device_id(None)
    hostname = platform.node()
    
    print("=" * 60)
    print("Device ID Auto-Detection Test")
    print("=" * 60)
    print(f"System hostname: {hostname}")
    print(f"Auto-detected device_id: {detected_id}")
    print()
    
    # Test 2: Explicit device_id provided (should use that)
    explicit_id = service._get_device_id("my-custom-device-123")
    print(f"Explicitly provided: my-custom-device-123")
    print(f"Used device_id: {explicit_id}")
    print()
    
    # Verify auto-detection logic
    expected = hostname.lower().replace(" ", "-").replace("_", "-")
    expected = "".join(c if c.isalnum() or c == "-" else "" for c in expected)
    
    if detected_id == expected:
        print("✅ Auto-detection works correctly!")
        print(f"   Firebase path will be: backups/{detected_id}/{{backup_id}}.zip")
    else:
        print(f"❌ Mismatch: expected '{expected}', got '{detected_id}'")
    
    if explicit_id == "my-custom-device-123":
        print("✅ Explicit device_id override works correctly!")
    else:
        print(f"❌ Override failed: expected 'my-custom-device-123', got '{explicit_id}'")
    
    print("=" * 60)


if __name__ == "__main__":
    test_device_autodetect()
