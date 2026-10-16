"""
Application factory.
Keeps the app creation separate from the module-level scope so that
tests can spin up isolated instances.
"""
import os
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from config.settings import ProductionConfig, get_config
from app.core.extensions import db, jwt, cors, limiter, migrate, _configure_celery
from sqlalchemy import text


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    # ── Configuration ─────────────────────────────────────────────────────
    config_class = get_config(config_name)
    if config_class is ProductionConfig:
        config_class.validate()
    app.config.from_object(config_class)
    from app.core.logging_setup import configure_production_logging, init_sentry

    if config_class is ProductionConfig:
        configure_production_logging(app)
        init_sentry(app)

    # ── Extensions ────────────────────────────────────────────────────────
    engine_options = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}))
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        for option in ("pool_size", "max_overflow", "pool_timeout"):
            engine_options.pop(option, None)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    _configure_celery(app)

    # ── ProxyFix for real client IP behind reverse proxy ───────────────────
    # Expected proxy chain in production:
    # Client IP -> Ingress / Cloud Reverse Proxy (Render / AWS ALB, 1 hop) -> Gunicorn (Flask WSGI)
    from werkzeug.middleware.proxy_fix import ProxyFix
    proxy_hops = int(os.getenv("PROXY_FIX_HOPS", "1"))
    if proxy_hops > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_hops, x_proto=proxy_hops)

    @jwt.additional_claims_loader
    def default_claims_callback(_identity):
        return {"aud": "customer"}

    # ── Global JWT user active status & session revocation enforcement ────
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(_jwt_header, jwt_data):
        from flask import request
        from app.models.user import User
        from app.models.audit_log import UsedRefreshToken
        from app.services.token_service import is_token_revoked
        identity = jwt_data.get("sub")
        if not identity:
            return True
        try:
            # Enforce audience separation:
            # Admin endpoints accept ONLY aud="admin"
            # Customer endpoints accept ONLY aud="customer"
            token_aud = jwt_data.get("aud")
            is_admin_path = request.path.startswith("/api/v1/admin")
            if is_admin_path and token_aud != "admin":
                return True
            if not is_admin_path and token_aud != "customer":
                return True

            user = db.session.get(User, int(identity))
            if user is None or not user.is_active:
                return True

            # If refresh token, check if already used (token reuse detection)
            jti = jwt_data.get("jti")
            if jwt_data.get("type") == "refresh" and jti:
                if UsedRefreshToken.query.filter_by(jti=jti).first() is not None:
                    from app.services.token_service import revoke_user_sessions
                    from app.services.audit_logger import record_audit_event, get_real_client_ip
                    revoke_user_sessions(user.id)
                    record_audit_event(
                        event_type="auth.refresh_token_reuse",
                        status="denied",
                        actor_id=user.id,
                        actor_email=user.email,
                        ip_address=get_real_client_ip(),
                        details={"jti": jti, "action": "revoke_all_sessions"},
                    )
                    return True

            # Check revocation timestamp for all token types
            if is_token_revoked(user.id, jwt_data):
                return True
            return False
        except Exception:
            # Fail closed on database errors or unexpected exceptions
            return True

    @jwt.revoked_token_loader
    def custom_revoked_token_loader(_jwt_header, jwt_data):
        from flask import request
        if request.path.startswith("/api/v1/admin"):
            return jsonify({"error": "Not found"}), 404
        if jwt_data.get("type") == "refresh":
            from app.models.audit_log import UsedRefreshToken
            if UsedRefreshToken.query.filter_by(jti=jwt_data.get("jti")).first() is not None:
                return jsonify({"error": "Invalid session. Token reuse detected. Please sign in again."}), 401
            return jsonify({"error": "Session has been revoked. Please sign in again."}), 401
        return jsonify({"error": "Account is disabled or session has been revoked."}), 403

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        from app.models.user import User
        identity = jwt_data.get("sub")
        if not identity:
            return None
        try:
            user = db.session.get(User, int(identity))
            if user is None or not user.is_active:
                return None
            return user
        except Exception:
            return None

    @jwt.user_lookup_error_loader
    def custom_user_lookup_error(_jwt_header, _jwt_data):
        from flask import request
        if request.path.startswith("/api/v1/admin"):
            return jsonify({"error": "Not found"}), 404
        return jsonify({"error": "Account is disabled or does not exist."}), 403

    @jwt.expired_token_loader
    def custom_expired_token_loader(_jwt_header, _jwt_data):
        from flask import request
        if request.path.startswith("/api/v1/admin"):
            return jsonify({"error": "Not found"}), 404
        return jsonify({"error": "Token has expired."}), 401

    @jwt.invalid_token_loader
    def custom_invalid_token_loader(error_string):
        from flask import request
        if request.path.startswith("/api/v1/admin"):
            return jsonify({"error": "Not found"}), 404
        return jsonify({"error": "Invalid token."}), 422

    @jwt.unauthorized_loader
    def custom_unauthorized_loader(error_string):
        from flask import request
        if request.path.startswith("/api/v1/admin"):
            return jsonify({"error": "Not found"}), 404
        return jsonify({"error": "Missing authorization header."}), 401

    with app.app_context():
        from app.models import user, scan, cloud, cloud_account, audit_log  # noqa: F401

    # ── CORS Handling (manual) ────────────────────────────────────────────
    # Initialize CORS with Flask-CORS extension
    cors_origins = app.config["CORS_ORIGINS"]
    if "*" in cors_origins:
        raise RuntimeError("CORS_ORIGINS must contain explicit origins, not *")

    import re
    # Expand wildcard subdomains (e.g. https://*.vercel.app) to regex patterns for Flask-CORS
    processed_origins = []
    for origin in cors_origins:
        if isinstance(origin, str) and origin.startswith("https://*."):
            suffix = re.escape(origin[len("https://*."):])
            processed_origins.append(re.compile(rf"^https://[a-zA-Z0-9_.-]+\.{suffix}$"))
        else:
            processed_origins.append(origin)

    cors.init_app(
        app,
        resources={r"/api/*": {
            "origins": processed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": bool(processed_origins),
            "max_age": 3600
        }}
    )

    @app.after_request
    def add_security_headers(response):
        if hasattr(response, "headers"):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
            )
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            if not app.config.get("DEBUG"):
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains"
                )
        return response

    # ── Error Handlers ────────────────────────────────────────────────────
    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def handle_405(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException):
            return jsonify({"error": error.name}), error.code
        app.logger.error("Unhandled exception: %s", type(error).__name__)
        return jsonify({"error": "Internal server error"}), 500

    # ── Blueprints ────────────────────────────────────────────────────────
    _register_blueprints(app)

    # ── Shell context ─────────────────────────────────────────────────────
    @app.shell_context_processor
    def make_shell_context():
        from app.models.user import User
        from app.models.scan import ScanJob, ScanResult, Vulnerability
        from app.models.cloud import CloudMetric
        from app.models.cloud_account import CloudAccount
        return {"db": db, "User": User, "ScanJob": ScanJob,
                "ScanResult": ScanResult, "Vulnerability": Vulnerability,
                "CloudMetric": CloudMetric, "CloudAccount": CloudAccount}

    # ── Health-check ──────────────────────────────────────────────────────
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "version": "1.0.0"})

    @app.get("/ready")
    def ready():
        checks = {
            "database": "ok" if _database_is_ready() else "unavailable",
            "redis": "ok" if _redis_is_ready() else "unavailable",
        }
        is_ready = all(status == "ok" for status in checks.values())
        return (
            {"status": "ready" if is_ready else "not_ready", "checks": checks},
            200 if is_ready else 503,
        )

    return app


def _database_is_ready() -> bool:
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        from flask import current_app

        current_app.logger.warning(
            "Readiness database check failed; exception_type=%s",
            type(exc).__name__,
        )
        return False


def _redis_is_ready() -> bool:
    from redis import Redis
    from flask import current_app

    try:
        with Redis.from_url(
            current_app.config["CELERY_BROKER_URL"],
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as redis_client:
            return bool(redis_client.ping())
    except Exception as exc:
        current_app.logger.warning(
            "Readiness Redis check failed; exception_type=%s",
            type(exc).__name__,
        )
        return False


def _register_blueprints(app: Flask):
    from app.api.v1.auth.routes import auth_bp
    from app.api.v1.scan.routes import scan_bp
    from app.api.v1.cloud.routes import cloud_bp
    from app.api.v1.reports.routes import reports_bp
    from app.api.v1.admin.routes import admin_bp
    from app.api.simple_api import simple_api_bp

    app.register_blueprint(auth_bp,      url_prefix="/api/v1/auth")
    app.register_blueprint(scan_bp,      url_prefix="/api/v1/scan")
    app.register_blueprint(cloud_bp,     url_prefix="/api/v1/cloud")
    app.register_blueprint(reports_bp,   url_prefix="/api/v1/reports")
    app.register_blueprint(admin_bp,     url_prefix="/api/v1/admin")
    app.register_blueprint(simple_api_bp, url_prefix="/api")