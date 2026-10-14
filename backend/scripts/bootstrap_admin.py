"""
Bootstrap admin user in Firestore.
Can be run standalone or called during startup.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.security import hash_password
from database.firebase import get_firestore


def bootstrap_admin(
    email: str = "rafidedward@gmail.com",
    full_name: str = "Rafid Edward",
    password: str = "Admin@1234",
    role: str = "admin",
):
    db = get_firestore()
    email_clean = (email or "").strip().lower()

    # Check if user already exists
    existing = list(
        db.collection("users").where("email", "==", email_clean).limit(1).stream()
    )
    if existing:
        print(f"[INFO] User {email_clean} already exists (ID: {existing[0].id}).")
        return existing[0].id

    now = datetime.now(timezone.utc)
    ref = db.collection("users").document()
    user_data = {
        "email": email_clean,
        "full_name": full_name,
        "hashed_password": hash_password(password),
        "role": role,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
        "last_login_ip": None,
        "is_online": False,
    }
    ref.set(user_data)
    print(f"[SUCCESS] Bootstrapped new admin user successfully!")
    print(f"  ID:       {ref.id}")
    print(f"  Email:    {email_clean}")
    print(f"  Fullname: {full_name}")
    print(f"  Role:     {role}")
    print(f"  Password: {password}")
    return ref.id


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "rafidedward@gmail.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "Admin@1234"
    full_name = sys.argv[3] if len(sys.argv) > 3 else "Rafid Edward"
    bootstrap_admin(email=email, full_name=full_name, password=password)
