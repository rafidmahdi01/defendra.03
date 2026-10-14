"""
Reset and wipe all collections from Firestore.
"""
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.firebase import get_firestore


def wipe_all_collections():
    db = get_firestore()
    collections = list(db.collections())
    print(f"Found {len(collections)} collections to wipe.")
    
    total_deleted = 0
    for coll in collections:
        coll_name = coll.id
        print(f"Wiping collection '{coll_name}'...")
        docs = list(coll.stream())
        batch = db.batch()
        batch_count = 0
        deleted_in_coll = 0
        
        for doc in docs:
            # Check for subcollections
            for subcoll in doc.reference.collections():
                for subdoc in subcoll.stream():
                    subdoc.reference.delete()
            
            batch.delete(doc.reference)
            batch_count += 1
            deleted_in_coll += 1
            total_deleted += 1
            
            if batch_count >= 400:
                batch.commit()
                batch = db.batch()
                batch_count = 0
                
        if batch_count > 0:
            batch.commit()
            
        print(f"  [OK] Deleted {deleted_in_coll} documents from '{coll_name}'")
        
    print(f"\n[DONE] Firestore wipe complete! Total documents deleted: {total_deleted}")


if __name__ == "__main__":
    wipe_all_collections()
