"""Test complete backup flow with Firebase upload."""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.backup_service import BackupService


def test_backup_with_firebase():
    """Test that backup creation uploads to Firebase."""
    print("=" * 60)
    print("Testing Complete Backup Flow with Firebase Upload")
    print("=" * 60)
    
    service = BackupService()
    
    # Check Firebase is enabled
    print(f"Firebase enabled: {service.firebase.enabled}")
    
    if not service.firebase.enabled:
        print("❌ Firebase NOT enabled - check your .env file!")
        return
    
    print(f"✅ Firebase configured:")
    print(f"   Bucket: {service.firebase.settings.firebase_storage_bucket}")
    print(f"   Credentials: {service.firebase.settings.firebase_service_account_json[:80]}...")
    print()
    
    # Create a test backup (manifest only - no real files)
    print("Creating test backup...")
    try:
        result = service.create_backup(
            paths=None,  # Will create manifest backup
            label="firebase-upload-test"
        )
        
        print("\n✅ Backup created successfully!")
        print(f"   Backup ID: {result['backup_id']}")
        print(f"   Device ID: {result['device_id']}")
        print(f"   Size: {result['size_bytes']} bytes")
        
        if result.get('firebase_uri'):
            print(f"   ✅ Firebase URI: {result['firebase_uri']}")
            print("\n🎉 SUCCESS! Backup uploaded to Firebase!")
        else:
            print("   ❌ No firebase_uri in result - upload may have failed")
            
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)


if __name__ == "__main__":
    test_backup_with_firebase()
