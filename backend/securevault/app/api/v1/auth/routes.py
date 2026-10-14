"""
Authentication endpoints.

POST  /api/v1/auth/register   – create a new account
POST  /api/v1/auth/login      – obtain access + refresh tokens
POST  /api/v1/auth/refresh    – exchange refresh token for new access token
GET   /api/v1/auth/me         – return current user profile
POST  /api/v1/auth/logout     – client-side: just discard the token
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)

from app.core.extensions import db, limiter
from app.models.user import User, RoleEnum

auth_bp = Blueprint("auth", __name__)


# ── Register ──────────────────────────────────────────────────────────────────

@auth_bp.post("/register")
@limiter.limit("10 per minute")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email    = (data.get("email")    or "").strip().lower()
    password = data.get("password")  or ""

    # ── Validation ────────────────────────────────────────────────────────
    errors = {}
    if not username or len(username) < 3:
        errors["username"] = "Must be at least 3 characters."
    if not email or "@" not in email:
        errors["email"] = "Must be a valid email address."
    if len(password) < 8:
        errors["password"] = "Must be at least 8 characters."
    if errors:
        return jsonify({"errors": errors}), 422

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken."}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409

    user = User(
        username=username,
        email=email,
        role=RoleEnum.VIEWER,
    )
    user.password = password
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Account created.", "user": user.to_dict()}), 201


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username") or data.get("email") or "").strip()
    password   = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "username/email and password are required."}), 400

    from datetime import datetime, timezone, timedelta
    from app.models.audit_log import AuditLog
    from app.services.audit_logger import record_audit_event, get_real_client_ip
    client_ip = get_real_client_ip()

    user = (
        User.query.filter_by(username=identifier).first()
        or User.query.filter_by(email=identifier.lower()).first()
    )

    # Per-account lockout check: 5 failed logins within 15 minutes
    account_key = user.email if user else identifier.lower()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    latest_success = (
        AuditLog.query.filter(
            AuditLog.actor_email == account_key,
            AuditLog.event_type == "auth.login_success",
        )
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    success_ts = latest_success.created_at if latest_success else cutoff
    if success_ts.tzinfo is None:
        success_ts = success_ts.replace(tzinfo=timezone.utc)
    check_since = max(cutoff, success_ts)

    failed_count = AuditLog.query.filter(
        AuditLog.actor_email == account_key,
        AuditLog.event_type == "auth.login_failed",
        AuditLog.created_at >= check_since,
    ).count()

    if failed_count >= 5:
        record_audit_event(
            event_type="auth.account_locked",
            status="denied",
            actor_id=user.id if user else None,
            actor_email=account_key,
            actor_role=user.role.value if (user and hasattr(user.role, "value")) else "unknown",
            ip_address=client_ip,
            details={"reason": "too_many_failed_logins", "attempts": failed_count},
        )
        return jsonify({"error": "Too many failed login attempts. Account temporarily locked for 15 minutes."}), 429

    if user is None or not user.verify_password(password):
        record_audit_event(
            event_type="auth.login_failed",
            status="denied",
            actor_id=user.id if user else None,
            actor_email=account_key,
            actor_role=user.role.value if (user and hasattr(user.role, "value")) else "unknown",
            ip_address=client_ip,
            details={"reason": "invalid_credentials"},
        )
        return jsonify({"error": "Invalid credentials."}), 401

    if not user.is_active:
        return jsonify({"error": "Account is disabled."}), 403

    record_audit_event(
        event_type="auth.login_success",
        status="success",
        actor_id=user.id,
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        ip_address=client_ip,
    )

    identity = str(user.id)
    access_token  = create_access_token(identity=identity, additional_claims={"aud": "customer"})
    refresh_token = create_refresh_token(identity=identity, additional_claims={"aud": "customer"})

    return jsonify({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user":          user.to_dict(),
    }), 200


# ── Refresh ───────────────────────────────────────────────────────────────────

@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        return jsonify({"error": "User not found or inactive."}), 401

    from flask_jwt_extended import get_jwt
    from app.services.token_service import is_token_revoked, revoke_user_sessions
    from app.models.audit_log import UsedRefreshToken
    from app.services.audit_logger import record_audit_event, get_real_client_ip

    jwt_payload = get_jwt()
    jti = jwt_payload.get("jti")
    client_ip = get_real_client_ip()

    if is_token_revoked(user_id):
        return jsonify({"error": "Session has been revoked. Please sign in again."}), 401

    # Refresh token reuse detection
    if jti and UsedRefreshToken.query.filter_by(jti=jti).first() is not None:
        revoke_user_sessions(user_id)
        record_audit_event(
            event_type="auth.refresh_token_reuse",
            status="denied",
            actor_id=user_id,
            actor_email=user.email,
            ip_address=client_ip,
            details={"jti": jti, "action": "revoke_all_sessions"},
        )
        return jsonify({"error": "Invalid session. Token reuse detected. Please sign in again."}), 401

    # Mark current refresh token as used
    if jti:
        used_token = UsedRefreshToken(jti=jti, user_id=user_id)
        db.session.add(used_token)
        db.session.commit()

    new_access = create_access_token(identity=str(user.id), additional_claims={"aud": "customer"})
    new_refresh = create_refresh_token(identity=str(user.id), additional_claims={"aud": "customer"})
    return jsonify({
        "access_token": new_access,
        "refresh_token": new_refresh,
    }), 200


# ── Me ────────────────────────────────────────────────────────────────────────

@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": user.to_dict()}), 200


# ── Logout (client-side token discard) ────────────────────────────────────────

@auth_bp.post("/logout")
@jwt_required()
def logout():
    # Stateless JWT — instruct the client to discard the token.
    # For server-side revocation, integrate a token blocklist (Redis) here.
    return jsonify({"message": "Logged out. Discard your tokens on the client."}), 200