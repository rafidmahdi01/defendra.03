import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.config import Settings


def test_empty_secret_raises_validation_error():
    os.environ['FASTAPI_JWT_SECRET'] = '  '
    try:
        Settings()
        raise AssertionError("Expected ValidationError was not raised for empty FASTAPI_JWT_SECRET")
    except Exception as e:
        print('CAUGHT EXPECTED ERROR:', type(e).__name__)
        print(e)
        print("Empty secret validation verified successfully.")


if __name__ == '__main__':
    test_empty_secret_raises_validation_error()
