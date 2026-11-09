import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("ENCRYPTION_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY ou ENCRYPTION_KEY é obrigatório.")

    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "natal2026")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

    SESSION_COOKIE_NAME = "amigo_sess"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool(os.getenv("SESSION_COOKIE_SECURE"), default=False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_REFRESH_EACH_REQUEST = True

    WTF_CSRF_TIME_LIMIT = 8 * 60 * 60
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]

    PARTICIPANT_COOKIE_NAME = "amigo_part"
    PARTICIPANT_COOKIE_MAX_AGE = 60 * 60 * 24 * 30

    FORCE_HTTPS = _bool(os.getenv("FORCE_HTTPS"), default=False)
    PREFERRED_URL_SCHEME = "https" if FORCE_HTTPS or SESSION_COOKIE_SECURE else "http"

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_DATABASE = os.getenv("DB_DATABASE", "postgres")
    DB_USER = os.getenv("DB_USER")
    DB_PSW = os.getenv("DB_PSW")
    DATABASE_URL = os.getenv("DATABASE_URL")

    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = "120 per hour"
