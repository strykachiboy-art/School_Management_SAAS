"""Application configuration for development, testing, and production."""

import os
from datetime import timedelta
from typing import Any


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)

    ADMIN_ACCESS_ENABLED = os.getenv("ADMIN_ACCESS_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    
    MAIL_HOST = os.getenv("MAIL_HOST", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@yourschoolapp.com")

    TESTING = False
    DEBUG = False


class DevelopmentConfig(Config):
    """Local development settings."""

    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL")
    ADMIN_ACCESS_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"

    SECRET_KEY = "testing-secret-key-not-for-production-use-only"
    JWT_SECRET_KEY = "testing-jwt-secret-key-not-for-production-use-only-please"


class ProductionConfig(Config):
    """Production settings."""

    DEBUG = False


config_by_name: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config_class(config_name: str | None = None) -> type[Config]:
    """Return a configuration class based on the current environment."""

    name = (config_name or os.getenv("FLASK_ENV", "development")).strip().lower()
    return config_by_name.get(name, DevelopmentConfig)


__all__ = [
    "Config",
    "DevelopmentConfig",
    "TestingConfig",
    "ProductionConfig",
    "get_config_class",
]