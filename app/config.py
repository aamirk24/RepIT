import os
from pathlib import Path


def normalize_database_url(url):
    """Use Psycopg 3 for PostgreSQL URLs supplied by hosting providers."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    JSON_SORT_KEYS = False


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

    @staticmethod
    def validate(instance_path):
        secret_key = os.environ.get("SECRET_KEY")
        database_url = os.environ.get("DATABASE_URL")
        if not secret_key or secret_key == "development-only-change-me":
            raise RuntimeError("Production requires a strong SECRET_KEY environment variable.")
        if not database_url:
            raise RuntimeError("Production requires a DATABASE_URL environment variable.")
        return {
            "SECRET_KEY": secret_key,
            "SQLALCHEMY_DATABASE_URI": normalize_database_url(database_url),
        }


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
