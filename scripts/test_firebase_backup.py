"""
Test script: Verify Firebase backup upload integration.

Tests:
1. Manual backup creation with device_id → should upload to Firebase
2. List backups filtered by device_id → should show only that device's backups
3. Verify Firebase URI is returned in metadata

Run from recovery_automation/:
    python -m scripts.test_firebase_backup
"""

import sys
from pathlib import Path

# Add recovery_automation to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "recovery_automation"))

import os
os.chdir(Path(__file__).resolve().parents[1] / "recovery_automation")

from dotenv import load_dotenv
load_dotenv()

from app.services.backup_service import BackupService
from app.utils.logger import get_logger

logger = get_logger("test_firebase_backup")

def test_firebase_backup_integration():
    """Test Firebase backup upload with device_id."""
    
    print("\n" + "="*70)
    print("Firebase Backup Integration Test")
    print("="*70)
    
    # Initialize service
    backup_service = BackupService()
    
    # Check Firebase configuration
    print("\n[1] Checking Firebase configuration...")
    if backup_service.firebase.enabled:
        print("    ✓ Firebase credentials configured")
    else:
        print("    ✗ Firebase NOT configured (check .env)")
        print("      Required: FIREBASE_SERVICE_ACCOUNT_JSON, FIREBASE_STORAGE_BUCKET")
        return
    
    # Create test backup with device_id
    print("\n[2] Creating test backup with device_id...")
    test_device_id = "test-device-001"
    test_paths = ["./app/utils"]  # Small directory for testing
    
    try:
        result = backup_service.create_backup(
            paths=test_paths,
            label="firebase-integration-test",
            device_id=test_device_id,
        )
        
        backup_id = result["backup_id"]
        firebase_uri = result.get("firebase_uri")
        
        print(f"    ✓ Backup created: {backup_id}")
        print(f"    ✓ Device ID: {test_device_id}")
        print(f"    ✓ Files: {result['file_count']}")
        print(f"    ✓ Size: {result['size_bytes']} bytes")
        
        if firebase_uri:
            print(f"    ✓ Firebase upload SUCCESS: {firebase_uri}")
        else:
            print(f"    ✗ Firebase upload FAILED (URI is None)")
            
    except Exception as e:
        print(f"    ✗ Backup creation failed: {e}")
        return
    
    # Test device filtering
    print(f"\n[3] Testing device filtering (device_id={test_device_id})...")
    filtered_backups = backup_service.list_backups(device_id=test_device_id)
    print(f"    ✓ Found {len(filtered_backups)} backup(s) for device {test_device_id}")
    
    # Verify our backup is in the filtered list
    found = any(b["backup_id"] == backup_id for b in filtered_backups)
    if found:
        print(f"    ✓ Created backup appears in filtered list")
    else:
        print(f"    ✗ Created backup NOT in filtered list")
    
    # Test admin view (no filter)
    print(f"\n[4] Testing admin view (no device filter)...")
    all_backups = backup_service.list_backups(device_id=None)
    print(f"    ✓ Found {len(all_backups)} total backup(s)")
    
    # Test filtering with wrong device_id
    print(f"\n[5] Testing negative case (wrong device_id)...")
    wrong_device_backups = backup_service.list_backups(device_id="nonexistent-device")
    print(f"    ✓ Found {len(wrong_device_backups)} backup(s) for nonexistent device (should be 0)")
    
    if len(wrong_device_backups) == 0:
        print(f"    ✓ Filtering works correctly")
    else:
        print(f"    ✗ Filtering may be broken")
    
    print("\n" + "="*70)
    print("Test complete!")
    print("="*70)
    print("\nSummary:")
    print(f"  • Backup ID: {backup_id}")
    print(f"  • Device ID: {test_device_id}")
    print(f"  • Firebase URI: {firebase_uri or 'NOT UPLOADED'}")
    print(f"  • Firebase Storage path: backups/{test_device_id}/{backup_id}.zip")
    print(f"\nVerify in Firebase Console:")
    print(f"  https://console.firebase.google.com/project/defendraai/storage")
    print()

if __name__ == "__main__":
    test_firebase_backup_integration()
