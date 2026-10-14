"""
Application configuration — Dev / Test / Prod.
All secrets are read from environment variables; sane defaults only for dev.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DEFAULT_DB_PATH = os.path.join(BASE_DIR, "instance", "securevault.db").replace("\\", "/")

def _normalize_database_url(db_url: str | None) -> str | None:
    if not db_url:
        return db_url
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]

    url = make_url(db_url)
    if url.drivername.startswith("postgresql"):
        local_hosts = {
            "localhost",
            "127.0.0.1",
            "::1",
            "postgres",
            "db",
            "host.docker.internal",
        }
        if (url.host or "").strip("[]").lower() not in local_hosts:
            url = url.update_query_dict({"sslmode": "require"}, append=False)
    return url.render_as_string(hide_password=False)


def _get_database_uri() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url or db_url.startswith("sqlite:///"):
        # Ensure SQLite always uses the absolute path to instance/securevault.db
        if not db_url or db_url in ("sqlite:///securevault.db", "sqlite:///instance/securevault.db"):
            return f"sqlite:///{DEFAULT_DB_PATH}"
    return _normalize_database_url(db_url) or f"sqlite:///{DEFAULT_DB_PATH}"


# ── Central Single Source of Truth for Provider Storage Capacity (GB) ──────
PROVIDER_STORAGE_CAPACITY_GB: dict = {
    "aws": 4,    # 4 GB (40%)
    "gcp": 3,    # 3 GB (30%)
    "azure": 3,  # 3 GB (30%)
}
TOTAL_STORAGE_CAPACITY_GB: int = 10


def get_provider_storage_capacity(provider: str) -> int:
    """
    Return the fixed storage capacity (in GB) for the given cloud provider.
    Serves as the single source of truth for before-and-after optimization checks.
    """
    key = (provider or "").strip().lower()
    return PROVIDER_STORAGE_CAPACITY_GB.get(key, 3)


class BaseConfig:
    # ── Cloud Provider Storage Capacity (Single Source of Truth) ─────────
    PROVIDER_STORAGE_CAPACITY_GB: dict = PROVIDER_STORAGE_CAPACITY_GB

    # ── Core ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development-only-secret")
    DEBUG: bool = False
    TESTING: bool = False
    ENABLE_DEMO_DATA: bool = False

    # ── Database ──────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI: str = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "2")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "1")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
    }

    # ── JWT ───────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "development-only-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "14"))
    )

    # ── Celery / Redis ────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_TASK_SOFT_TIME_LIMIT: int = int(
        os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "240")
    )
    CELERY_TASK_TIME_LIMIT: int = int(os.getenv("CELERY_TASK_TIME_LIMIT", "300"))
    CELERY_BROKER_CONNECTION_TIMEOUT: int = int(
        os.getenv("CELERY_BROKER_CONNECTION_TIMEOUT", "5")
    )
    CELERY_TASK_PUBLISH_MAX_RETRIES: int = int(
        os.getenv("CELERY_TASK_PUBLISH_MAX_RETRIES", "1")
    )

    # ── Rate limiting ─────────────────────────────────────────────────────
    RATELIMIT_STORAGE_URI: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    RATELIMIT_DEFAULT: str = "200 per day;50 per hour"

    # ── Demo Mode ─────────────────────────────────────────────────────────
    ENABLE_DEMO_DATA: bool = os.getenv("ENABLE_DEMO_DATA", "false").lower() == "true"

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    ADMIN_CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv("ADMIN_CORS_ORIGINS", "http://localhost:5174").split(",")
        if origin.strip()
    ]
    ADMIN_IP_ALLOWLIST: str = os.getenv("ADMIN_IP_ALLOWLIST", "")

    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", os.getenv("CLOUD_ENCRYPTION_KEY", ""))
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GEMINI_DAILY_USER_QUOTA: int = int(os.getenv("GEMINI_DAILY_USER_QUOTA", "25"))
    GEMINI_DAILY_GLOBAL_CAP: int = int(os.getenv("GEMINI_DAILY_GLOBAL_CAP", "500"))
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_REQUEST_TIMEOUT_SECONDS: float = float(
        os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "10")
    )
    GEMINI_CIRCUIT_BREAKER_FAILURES: int = int(
        os.getenv("GEMINI_CIRCUIT_BREAKER_FAILURES", "3")
    )
    GEMINI_CIRCUIT_BREAKER_RESET_SECONDS: int = int(
        os.getenv("GEMINI_CIRCUIT_BREAKER_RESET_SECONDS", "300")
    )
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

    # ── Scanner ───────────────────────────────────────────────────────────
    CLONE_BASE_DIR: str = os.getenv("CLONE_BASE_DIR", "/tmp/securevault_repos")
    MAX_REPO_SIZE_MB: int = int(os.getenv("MAX_REPO_SIZE_MB", "500"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ENABLE_DEMO_DATA = os.getenv("ENABLE_DEMO_DATA", "true").lower() == "true"
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )
    CELERY_TASK_ALWAYS_EAGER = True   # run tasks synchronously in tests
    CELERY_TASK_EAGER_PROPAGATES = True
    RATELIMIT_ENABLED = False


class ProductionConfig(BaseConfig):
    SECRET_KEY: str = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI: str = _normalize_database_url(
        os.environ.get("DATABASE_URL")
    )
    ENCRYPTION_KEY: str = os.environ.get("ENCRYPTION_KEY")
    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    RATELIMIT_STORAGE_URI: str = os.environ.get("REDIS_URL", "")
    ENABLE_DEMO_DATA = False
    DEBUG = False
    PROPAGATE_EXCEPTIONS = False

    @classmethod
    def validate(cls) -> None:
        required_variables = (
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "DATABASE_URL",
            "ENCRYPTION_KEY",
            "CORS_ORIGINS",
            "REDIS_URL",
        )
        for variable in required_variables:
            if not os.environ.get(variable, "").strip():
                raise RuntimeError(
                    f"Missing required production environment variable: {variable}"
                )
        if not cls.CORS_ORIGINS:
            raise RuntimeError(
                "Missing required production environment variable: CORS_ORIGINS"
            )
        if "*" in cls.CORS_ORIGINS:
            raise RuntimeError("CORS_ORIGINS must contain explicit origins, not *")
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str = "development"):
    return config_map.get(name, DevelopmentConfig)