import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("sqlalchemy_database_uri", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("secret_key", "testsecret")
os.environ.setdefault("algorithm", "HS256")

os.environ.setdefault("mail_username", "test@example.com")
os.environ.setdefault("mail_password", "password")
os.environ.setdefault("mail_from", "noreply@example.com")
os.environ.setdefault("mail_port", "587")
os.environ.setdefault("mail_server", "smtp.example.com")

os.environ.setdefault("cloudinary_name", "demo")
os.environ.setdefault("cloudinary_api_key", "1234567890")
os.environ.setdefault("cloudinary_api_secret", "secret")

os.environ.setdefault("DISABLE_RATE_LIMITER", "1")
