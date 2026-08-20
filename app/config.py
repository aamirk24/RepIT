import os
from datetime import timedelta
from pathlib import Path


def normalize_database_url(url):
    """Use Psycopg 3 for PostgreSQL URLs supplied by hosting providers."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def environment_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError as error:
        raise RuntimeError(f"{name} must be a number.") from error


def environment_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer.") from error


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_WINDOW = timedelta(minutes=15)
    LOGIN_BLOCK_DURATION = timedelta(minutes=15)
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    JSON_SORT_KEYS = False
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "text").lower()
    SENTRY_DSN = os.environ.get("SENTRY_DSN")
    SENTRY_TRACES_SAMPLE_RATE = environment_float("SENTRY_TRACES_SAMPLE_RATE", "0.0")
    PROXY_FIX_HOPS = 0


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "development-only-change-me")

    @staticmethod
    def database_uri(instance_path):
        return normalize_database_url(
            os.environ.get("DATABASE_URL", f"sqlite:///{Path(instance_path) / 'repit.db'}")
        )


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"
    SESSION_REFRESH_EACH_REQUEST = False
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "json").lower()

    @staticmethod
    def validate(instance_path):
        secret_key = os.environ.get("SECRET_KEY")
        database_url = os.environ.get("DATABASE_URL")
        if not secret_key or secret_key == "development-only-change-me" or len(secret_key) < 32:
            raise RuntimeError("Production requires a SECRET_KEY of at least 32 characters.")
        if not database_url:
            raise RuntimeError("Production requires a DATABASE_URL environment variable.")
        if not database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
            raise RuntimeError("Production DATABASE_URL must use PostgreSQL.")
        proxy_hops = environment_int("PROXY_FIX_HOPS", "1")
        if proxy_hops not in {0, 1, 2}:
            raise RuntimeError("PROXY_FIX_HOPS must be 0, 1, or 2.")
        log_format = os.environ.get("LOG_FORMAT", "json").lower()
        if log_format not in {"text", "json"}:
            raise RuntimeError("LOG_FORMAT must be 'text' or 'json'.")
        traces_sample_rate = environment_float("SENTRY_TRACES_SAMPLE_RATE", "0.0")
        if not 0 <= traces_sample_rate <= 1:
            raise RuntimeError("SENTRY_TRACES_SAMPLE_RATE must be between 0 and 1.")
        pool_size = environment_int("DATABASE_POOL_SIZE", "5")
        max_overflow = environment_int("DATABASE_MAX_OVERFLOW", "5")
        if pool_size < 1 or max_overflow < 0:
            raise RuntimeError("DATABASE_POOL_SIZE must be positive and DATABASE_MAX_OVERFLOW cannot be negative.")
        return {
            "SECRET_KEY": secret_key,
            "SQLALCHEMY_DATABASE_URI": normalize_database_url(database_url),
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_pre_ping": True,
                "pool_recycle": 300,
                "pool_size": pool_size,
                "max_overflow": max_overflow,
            },
            "PROXY_FIX_HOPS": proxy_hops,
            "LOG_FORMAT": log_format,
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO").upper(),
            "SENTRY_DSN": os.environ.get("SENTRY_DSN"),
            "SENTRY_TRACES_SAMPLE_RATE": traces_sample_rate,
        }


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
