import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _emails(value):
    if not value:
        return []
    return [addr.strip() for addr in value.split(",") if addr.strip()]


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    FLASK_DEBUG = _bool(os.environ.get("FLASK_DEBUG"), default=False)

    _db_path = os.environ.get("DATABASE_PATH", "instance/downtime.db")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + str((BASE_DIR / _db_path).resolve())
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or 587)
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = _bool(os.environ.get("SMTP_USE_TLS"), default=True)
    SMTP_FROM = os.environ.get("SMTP_FROM", "downtime-tracker@example.com")

    REMINDER_EMAIL = _emails(os.environ.get("REMINDER_EMAIL", ""))
    REMINDER_INTERVAL_MINUTES = int(os.environ.get("REMINDER_INTERVAL_MINUTES", "240") or 240)
    REMINDER_ACTIVE_START_HOUR = int(os.environ.get("REMINDER_ACTIVE_START_HOUR", "7") or 7)
    REMINDER_ACTIVE_END_HOUR = int(os.environ.get("REMINDER_ACTIVE_END_HOUR", "19") or 19)


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SCHEDULER_ENABLED = False


class CliConfig(Config):
    """Used by report_status.py: a one-shot script has no business starting
    a background reminder scheduler that will just die when it exits."""

    SCHEDULER_ENABLED = False
