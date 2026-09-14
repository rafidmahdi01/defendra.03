"""
Delete demo data from Defendra.
This script removes all sample devices and alerts that were added by populate_demo_data.py.
It only deletes documents with 'sample_data': True flag.
"""

import sys
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.firebase import get_firestore


def delete_demo_data():
    """Delete all demo data from Firebase."""
    db = get_firestore()
    
    print("🗑️  Starting demo data cleanup...\n")
    
    # Delete sample devices
    print("📱 Deleting sample devices...")
    devices_query = db.collection("devices").where("sample_data", "==", True)
    devices_deleted = 0
    batch = db.batch()
    batch_count = 0
    
    for doc in devices_query.stream():
        batch.delete(doc.reference)
        batch_count += 1
        devices_deleted += 1
        device_data = doc.to_dict()
        print(f"  ✓ Deleting device: {device_data.get('hostname', 'Unknown')}")
        
        # Firestore batch limit is 500 operations
        if batch_count >= 450:
            batch.commit()
            batch = db.batch()
            batch_count = 0
    
    if batch_count > 0:
        batch.commit()
    
    print(f"\n✅ Deleted {devices_deleted} sample devices\n")
    
    # Delete sample alerts
    print("🚨 Deleting sample alerts...")
    alerts_query = db.collection("alerts").where("sample_data", "==", True)
    alerts_deleted = 0
    batch = db.batch()
    batch_count = 0
    
    for doc in alerts_query.stream():
        batch.delete(doc.reference)
        batch_count += 1
        alerts_deleted += 1
        alert_data = doc.to_dict()
        print(f"  ✓ Deleting alert: {alert_data.get('title', 'Unknown')}")
        
        # Firestore batch limit is 500 operations
        if batch_count >= 450:
            batch.commit()
            batch = db.batch()
            batch_count = 0
    
    if batch_count > 0:
        batch.commit()
    
    print(f"\n✅ Deleted {alerts_deleted} sample alerts\n")
    
    # Summary
    print("=" * 60)
    print("🧹 DEMO DATA CLEANUP COMPLETE")
    print("=" * 60)
    print(f"✓ Devices Deleted: {devices_deleted}")
    print(f"✓ Alerts Deleted: {alerts_deleted}")
    print(f"✓ Total Items Removed: {devices_deleted + alerts_deleted}")
    print("=" * 60)
    
    if devices_deleted == 0 and alerts_deleted == 0:
        print("\n💡 No demo data found. All sample data has already been removed.")
    else:
        print("\n✨ Your database is now clean of demo data!")


if __name__ == "__main__":
    try:
        delete_demo_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
