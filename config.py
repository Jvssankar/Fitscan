import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "fitscan-dev-secret-2024-change-me")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = "claude-sonnet-4-6"

    _db = os.environ.get("DATABASE_URL", "")
    if _db.startswith("postgres://"):
        _db = _db.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db or "sqlite:///fitscan.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REFRESH_SECRET = os.environ.get("REFRESH_SECRET", "refresh-secret-change-me")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
