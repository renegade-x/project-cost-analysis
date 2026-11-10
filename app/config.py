"""Environment-driven configuration; secrets are resolved at app creation."""
import os
import secrets
from datetime import timedelta


class Config:
    SECRET_KEY = None
    SQLALCHEMY_DATABASE_URI = "sqlite:///cost_analyzer.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    MAX_UPLOAD_ROWS = 1000
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    GEMINI_API_KEY = None
    GEMINI_MODEL = "gemini-2.5-flash"
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_DEFAULT = "200 per hour"
    PRODUCTION = False
    DEBUG = False


class ProductionConfig(Config):
    PRODUCTION = True
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "only-for-isolated-tests"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


def configure_environment(app) -> None:
    """Resolve fresh values, so factories and tests never reuse stale environment."""
    if not app.testing:
        app.config.update(
            SECRET_KEY=os.environ.get("SECRET_KEY") or None,
            SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL")
            or "sqlite:///cost_analyzer.db",
            GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY"),
            GEMINI_MODEL=os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash",
        )
    if app.config["PRODUCTION"] and not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY must be set in production")
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = secrets.token_hex(32)
    if app.config["PRODUCTION"]:
        app.config["DEBUG"] = False
