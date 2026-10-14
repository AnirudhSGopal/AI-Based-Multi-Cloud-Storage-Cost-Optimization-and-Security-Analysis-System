"""
Custom decorators for role-based access control and admin security.
"""
from functools import wraps
import os

from flask import abort, jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.core.extensions import db
from app.models.user import User, RoleEnum
from app.services.audit_logger import record_audit_event, get_real_client_ip


def roles_required(*roles: RoleEnum):
    """Allow only users whose role is in *roles*."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = _get_current_user()
            if user is None:
                return jsonify({"error": "User not found"}), 404
            if not user.has_role(*roles):
                return jsonify({"error": "Insufficient permissions"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def analyst_or_above(fn):
    """Allow admin and analyst roles."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _get_current_user()
        if user is None:
            return jsonify({"error": "User not found"}), 404
        if not user.is_analyst_or_above():
            return jsonify({"error": "Analyst or above required"}), 403
        return fn(*args, **kwargs)
    return wrapper


def active_user_required(fn):
    """Reject deactivated accounts."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _get_current_user()
        if user is None:
            return jsonify({"error": "User not found"}), 404
        if not user.is_active:
            return jsonify({"error": "Account is disabled"}), 403
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    """
    Allow only active admin users.
    Returns 404 for unauthenticated callers, invalid/tampered tokens, non-admin users,
    or inactive users so the existence of admin routes is never revealed.
    Emits distinct audit events for failed access attempts.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        client_ip = get_real_client_ip()

        # 0. Check optional IP allowlist for admin endpoints
        allowlist = (os.getenv("ADMIN_IP_ALLOWLIST") or "").strip()
        if allowlist:
            import ipaddress
            is_allowed = False
            try:
                client_addr = ipaddress.ip_address(client_ip)
                for net in allowlist.split(","):
                    net = net.strip()
                    if not net:
                        continue
                    if "/" not in net:
                        net += "/32" if ":" not in net else "/128"
                    if client_addr in ipaddress.ip_network(net, strict=False):
                        is_allowed = True
                        break
            except Exception:
                is_allowed = False
            if not is_allowed:
                record_audit_event(
                    event_type="admin.access_denied",
                    status="denied",
                    actor_role="anonymous",
                    ip_address=client_ip,
                    details={"reason": "ip_not_allowlisted"},
                )
                return jsonify({"error": "Not found"}), 404

        # 1. Verify JWT — catch missing, expired, or tampered tokens
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            user_id = int(identity) if identity is not None else None
        except Exception as exc:
            actor_id = None
            try:
                from flask_jwt_extended import decode_token
                auth_hdr = request.headers.get("Authorization", "")
                if auth_hdr.startswith("Bearer "):
                    raw_token = auth_hdr.split(" ", 1)[1].strip()
                    dec = decode_token(raw_token, allow_expired=True)
                    if dec and dec.get("sub"):
                        actor_id = int(dec.get("sub"))
            except Exception:
                pass
            record_audit_event(
                event_type="admin.access_denied",
                status="denied",
                actor_id=actor_id,
                actor_role="anonymous" if actor_id is None else "unknown",
                ip_address=client_ip,
                details={
                    "reason": "unauthenticated_or_tampered_token",
                    "exception": type(exc).__name__,
                },
            )
            return jsonify({"error": "Not found"}), 404

        # 2. Enforce token audience (must be aud=admin)
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        if claims.get("aud") != "admin":
            record_audit_event(
                event_type="admin.access_denied",
                status="denied",
                actor_id=user_id,
                actor_role="unknown",
                ip_address=client_ip,
                details={"reason": "invalid_audience", "token_aud": claims.get("aud")},
            )
            return jsonify({"error": "Not found"}), 404

        # 3. Verify user from database on every request
        user = db.session.get(User, user_id)
        if user is None:
            record_audit_event(
                event_type="admin.access_denied",
                status="denied",
                actor_id=user_id,
                actor_role="unknown",
                ip_address=client_ip,
                details={"reason": "user_not_found"},
            )
            return jsonify({"error": "Not found"}), 404

        if not user.is_active:
            record_audit_event(
                event_type="admin.access_denied",
                status="denied",
                actor_id=user.id,
                actor_email=user.email,
                actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
                ip_address=client_ip,
                details={"reason": "account_disabled"},
            )
            return jsonify({"error": "Not found"}), 404

        if not user.is_admin():
            record_audit_event(
                event_type="admin.access_denied",
                status="denied",
                actor_id=user.id,
                actor_email=user.email,
                actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
                ip_address=client_ip,
                details={"reason": "insufficient_permissions", "actual_role": str(user.role)},
            )
            return jsonify({"error": "Not found"}), 404

        from app.services.token_service import is_token_revoked
        if is_token_revoked(user.id):
            record_audit_event(
                event_type="admin.access_denied",
                status="denied",
                actor_id=user.id,
                actor_email=user.email,
                actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
                ip_address=client_ip,
                details={"reason": "session_revoked"},
            )
            return jsonify({"error": "Not found"}), 404

        return fn(*args, **kwargs)

    return wrapper


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_current_user() -> User | None:
    """Return the User object from the JWT identity claim."""
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        abort(401)
    return db.session.get(User, user_id)