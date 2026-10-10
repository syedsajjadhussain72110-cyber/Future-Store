"""
Future Store — Configuration
Dev / Prod settings separation.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


class Config:
    """Base configuration shared by all environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # ── MongoDB ──────────────────────────────────────────────────────────────
    # Local MongoDB instance by default. Override via env vars in production
    # (e.g. a MongoDB Atlas connection string).
    MONGO_URI  = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB   = os.environ.get("MONGO_DB", "future_store")

    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # In production, set SECRET_KEY via environment variable


config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}