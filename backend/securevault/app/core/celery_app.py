"""
Celery worker entry point for CloudOpt background scanner.
Usage:
    celery -A app.core.celery_app worker --loglevel=INFO --concurrency=2
"""
import os
from app.core.factory import create_app
from app.core.extensions import celery

flask_app = create_app(os.getenv("FLASK_ENV", "production"))
# Ensure task modules are imported and registered
import app.tasks.scan_tasks  # noqa: F401

app = celery
celery_app = celery

__all__ = ["celery", "celery_app", "app", "flask_app"]
