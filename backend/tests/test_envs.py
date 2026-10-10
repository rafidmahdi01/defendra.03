import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
root_dir = backend_dir.parent

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load .env from root or backend directory
env_path = root_dir / '.env'
if not env_path.exists():
    env_path = backend_dir / '.env'
load_dotenv(env_path)

from utils.config import get_settings


def test_environment_variables():
    print('SECRET:', repr(os.environ.get('FASTAPI_JWT_SECRET')))
    print('SMTP:', repr(os.environ.get('SMTP_PASSWORD')))
    settings = get_settings()
    print('SETTINGS SMTP:', settings.smtp_password)
    assert settings.fastapi_jwt_secret, "FASTAPI_JWT_SECRET must not be empty"
    print("Environment variables loaded and verified successfully.")


if __name__ == '__main__':
    test_environment_variables()
