"""
Quick test to verify backup routes work without authentication.
"""
import requests

RECOVERY_URL = "http://127.0.0.1:8001"

def test_list_backups():
    """Test listing backups without auth token."""
    print("Testing GET /backup/list (no auth)...")
    response = requests.get(f"{RECOVERY_URL}/backup/list", timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200, "Should work without auth"
    print("  ✓ Works without authentication!")

def test_get_schedule():
    """Test getting schedule without auth token."""
    print("\nTesting GET /backup/schedule (no auth)...")
    response = requests.get(f"{RECOVERY_URL}/backup/schedule", timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200, "Should work without auth"
    print("  ✓ Works without authentication!")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Backup System WITHOUT Authentication")
    print("=" * 60)
    print("\nMake sure recovery service is running on port 8001")
    print("Run: cd recovery_automation && python -m uvicorn app.main:app --port 8001\n")
    
    try:
        test_list_backups()
        test_get_schedule()
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - No authentication required!")
        print("=" * 60)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to recovery service on port 8001")
        print("Please start it first: cd recovery_automation && python -m uvicorn app.main:app --port 8001")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
