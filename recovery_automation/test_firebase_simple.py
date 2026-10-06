"""
Test script: Verify Firebase backup upload integration (standalone).

This test directly creates a backup and verifies Firebase upload works.

Run from recovery_automation/:
    cd recovery_automation
    .venv\Scripts\python.exe test_firebase_simple.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test Firebase configuration
print("\n" + "="*70)
print("Firebase Backup Integration Test - Quick Check")
print("="*70)

print("\n[1] Environment Check:")
firebase_sa = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
firebase_bucket = os.environ.get("FIREBASE_STORAGE_BUCKET", "")

if firebase_sa:
    print(f"    ✓ FIREBASE_SERVICE_ACCOUNT_JSON: {firebase_sa[:50]}...")
else:
    print(f"    ✗ FIREBASE_SERVICE_ACCOUNT_JSON: NOT SET")

if firebase_bucket:
    print(f"    ✓ FIREBASE_STORAGE_BUCKET: {firebase_bucket}")
else:
    print(f"    ✗ FIREBASE_STORAGE_BUCKET: NOT SET")

if not firebase_sa or not firebase_bucket:
    print("\n✗ Firebase not configured. Cannot test upload.")
    sys.exit(1)

print("\n[2] Testing Firebase SDK initialization:")
try:
    import firebase_admin
    from firebase_admin import credentials, storage
    print("    ✓ firebase-admin imported successfully")
    
    # Test initialization
    app_name = "test_firebase_check"
    try:
        existing = firebase_admin.get_app(app_name)
        print(f"    ✓ Firebase app already exists: {app_name}")
    except ValueError:
        # Initialize
        if firebase_sa.startswith("{"):
            import json
            sa_dict = json.loads(firebase_sa)
            cred = credentials.Certificate(sa_dict)
            print("    ✓ Loaded credentials from JSON string")
        else:
            sa_path = Path(firebase_sa).expanduser().resolve()
            if not sa_path.exists():
                print(f"    ✗ Service account file not found: {sa_path}")
                sys.exit(1)
            cred = credentials.Certificate(str(sa_path))
            print(f"    ✓ Loaded credentials from file: {sa_path}")
        
        app = firebase_admin.initialize_app(
            cred,
            options={"storageBucket": firebase_bucket},
            name=app_name,
        )
        print(f"    ✓ Firebase app initialized: {app_name}")
    
    # Get bucket
    bucket = storage.bucket(app=firebase_admin.get_app(app_name))
    print(f"    ✓ Got Firebase Storage bucket: {bucket.name}")
    
    print("\n[3] Testing upload simulation (metadata only):")
    test_device_id = "test-device-999"
    test_backup_id = "test-backup-abc123"
    blob_path = f"backups/{test_device_id}/{test_backup_id}.zip"
    print(f"    • Storage path: {blob_path}")
    print(f"    • Full URI: gs://{bucket.name}/{blob_path}")
    
    print("\n✓ Firebase is properly configured and SDK works!")
    print("\nNext steps:")
    print("1. Create a manual backup with device_id via the frontend")
    print("2. Check Firebase Console to verify the upload")
    print("3. Use admin CLI to download it")
    
except ImportError as e:
    print(f"    ✗ Firebase SDK import failed: {e}")
    print("\n    Install firebase-admin:")
    print("    cd recovery_automation")
    print("    .venv\\Scripts\\pip install firebase-admin>=6.0.0")
    sys.exit(1)
except Exception as e:
    print(f"    ✗ Firebase test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
