"""
Admin API endpoints — platform management for admin users.

All routes are protected by @limiter.limit("120 per minute") + @admin_required.
Non-admin callers unconditionally receive 404 Not Found to prevent route enumeration.
Blueprint prefix: /api/v1/admin
"""
import os
import logging
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func

from app.core.extensions import db, limiter
from app.utils.decorators import admin_required
from app.models.user import User, RoleEnum
from app.models.cloud_account import CloudAccount, AccountStatusEnum
from app.models.cloud import CloudMetric, CloudProviderEnum
from app.models.scan import ScanJob, ScanStatusEnum
from app.models.audit_log import AuditLog
from app.services.audit_logger import record_audit_event
from app.services.token_service import revoke_user_sessions

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)


def _get_caller_admin() -> User:
    """Return the authenticated admin making the request."""
    admin_id = int(get_jwt_identity())
    return db.session.get(User, admin_id)


from datetime import datetime, timezone, timedelta
from app.services.audit_logger import get_real_client_ip
from flask_jwt_extended import create_access_token

LOCKOUT_WINDOW_SECONDS = 15 * 60  # 15 minutes
MAX_REAUTH_FAILURES = 5


def _is_ip_allowlisted() -> bool:
    allowlist = (os.getenv("ADMIN_IP_ALLOWLIST") or "").strip()
    if not allowlist:
        return True
    import ipaddress
    client_ip = get_real_client_ip()
    try:
        client_addr = ipaddress.ip_address(client_ip)
        for net_str in allowlist.split(","):
            net_str = net_str.strip()
            if not net_str:
                continue
            if "/" not in net_str:
                net_str += "/32" if ":" not in net_str else "/128"
            if client_addr in ipaddress.ip_network(net_str, strict=False):
                return True
        return False
    except Exception:
        return False


def _is_admin_reauth_locked(admin_id: int) -> bool:
    """Durable DB-backed check: counts admin.reauth_failed audit events in last 15 min since latest success."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=LOCKOUT_WINDOW_SECONDS)
    latest_success = (
        AuditLog.query.filter(
            AuditLog.actor_id == admin_id,
            AuditLog.event_type.in_(("admin.reauth_success", "admin.login_success")),
        )
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    success_ts = latest_success.created_at if latest_success else cutoff
    if success_ts.tzinfo is None:
        success_ts = success_ts.replace(tzinfo=timezone.utc)
    check_since = max(cutoff, success_ts)

    count = AuditLog.query.filter(
        AuditLog.actor_id == admin_id,
        AuditLog.event_type == "admin.reauth_failed",
        AuditLog.created_at >= check_since,
    ).count()
    return count >= MAX_REAUTH_FAILURES


def _clear_reauth_failures(admin_id: int) -> None:
    """Record admin.reauth_success to clear and reset the failure window."""
    record_audit_event(
        event_type="admin.reauth_success",
        status="success",
        actor_id=admin_id,
    )


def _verify_admin_password_confirmation(caller: User, payload: dict) -> tuple[bool, str | None]:
    """
    Verify admin password re-entry for high-impact mutations.
    Durable lockout enforced from AuditLog records.
    Returns (True, None) or (False, error_message).
    """
    if _is_admin_reauth_locked(caller.id):
        record_audit_event(
            event_type="admin.reauth_locked",
            status="denied",
            actor_id=caller.id,
            actor_email=caller.email,
            actor_role=caller.role.value if hasattr(caller.role, "value") else str(caller.role),
            details={"reason": "lockout_active", "max_attempts": MAX_REAUTH_FAILURES},
        )
        return False, "Too many failed password confirmations. Account locked for re-authentication for 15 minutes."

    pwd = (
        payload.get("admin_password")
        or payload.get("confirm_password")
        or request.headers.get("X-Admin-Password")
        or request.args.get("admin_password")
    )
    if not pwd or not isinstance(pwd, str):
        record_audit_event(
            event_type="admin.reauth_failed",
            status="denied",
            actor_id=caller.id,
            actor_email=caller.email,
            actor_role=caller.role.value if hasattr(caller.role, "value") else str(caller.role),
            details={"reason": "missing_password_confirmation"},
        )
        return False, "Admin password confirmation required."

    is_valid = caller.verify_password(pwd.strip())
    if not is_valid:
        record_audit_event(
            event_type="admin.reauth_failed",
            status="denied",
            actor_id=caller.id,
            actor_email=caller.email,
            actor_role=caller.role.value if hasattr(caller.role, "value") else str(caller.role),
            details={"reason": "invalid_password_confirmation"},
        )
        if _is_admin_reauth_locked(caller.id):
            record_audit_event(
                event_type="admin.reauth_locked",
                status="denied",
                actor_id=caller.id,
                actor_email=caller.email,
                actor_role=caller.role.value if hasattr(caller.role, "value") else str(caller.role),
                details={"reason": "threshold_reached"},
            )
            return False, "Too many failed password confirmations. Account locked for re-authentication for 15 minutes."

        return False, "Invalid admin password confirmation."

    record_audit_event(
        event_type="admin.reauth_success",
        status="success",
        actor_id=caller.id,
        actor_email=caller.email,
        actor_role=caller.role.value if hasattr(caller.role, "value") else str(caller.role),
    )
    return True, None


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN AUTHENTICATION & LOGIN (aud="admin")
# ═══════════════════════════════════════════════════════════════════════════════


@admin_bp.post("/auth/login")
@limiter.limit("10 per minute")
def admin_login():
    """
    POST /api/v1/admin/auth/login
    Dedicated authentication endpoint for administrators.
    Requires active admin account, password, and optional TOTP MFA.
    Enforces IP allowlisting and issues short-lived 15-minute token with claim aud="admin".
    """
    if not _is_ip_allowlisted():
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    identifier = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""
    totp_code = (data.get("totp_code") or data.get("mfa_code") or "").strip()

    if not identifier or not password:
        return jsonify({"error": "Invalid credentials."}), 401

    user = (
        User.query.filter_by(username=identifier).first()
        or User.query.filter_by(email=identifier.lower()).first()
    )

    client_ip = get_real_client_ip()

    # Generic 404 for non-existent, non-admin, or disabled user to hide existence
    if user is None or not user.is_admin() or not user.is_active:
        record_audit_event(
            event_type="admin.login_failed",
            status="denied",
            actor_email=identifier.lower(),
            actor_role="unknown",
            ip_address=client_ip,
            details={"reason": "invalid_user_or_not_admin"},
        )
        return jsonify({"error": "Not found"}), 404

    if _is_admin_reauth_locked(user.id):
        record_audit_event(
            event_type="admin.reauth_locked",
            status="denied",
            actor_id=user.id,
            actor_email=user.email,
            actor_role=user.role.value,
            ip_address=client_ip,
            details={"reason": "lockout_active"},
        )
        return jsonify({"error": "Too many failed attempts. Account temporarily locked for 15 minutes."}), 429

    if not user.verify_password(password):
        record_audit_event(
            event_type="admin.reauth_failed",
            status="denied",
            actor_id=user.id,
            actor_email=user.email,
            actor_role=user.role.value,
            ip_address=client_ip,
            details={"reason": "invalid_admin_password"},
        )
        return jsonify({"error": "Invalid credentials."}), 401

    # MFA (TOTP) verification if user has totp_secret configured
    if user.totp_secret:
        if not totp_code or not user.verify_totp(totp_code):
            record_audit_event(
                event_type="admin.mfa_failed",
                status="denied",
                actor_id=user.id,
                actor_email=user.email,
                actor_role=user.role.value,
                ip_address=client_ip,
                details={"reason": "invalid_or_missing_totp"},
            )
            return jsonify({"error": "Invalid or missing MFA code."}), 401

    record_audit_event(
        event_type="admin.login_success",
        status="success",
        actor_id=user.id,
        actor_email=user.email,
        actor_role=user.role.value,
        ip_address=client_ip,
    )

    admin_token = create_access_token(
        identity=str(user.id),
        additional_claims={"aud": "admin"},
        expires_delta=timedelta(minutes=15),
    )

    return jsonify({
        "access_token": admin_token,
        "token_type": "Bearer",
        "expires_in": 900,
        "user": user.to_dict(),
    }), 200


# ═══════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@admin_bp.get("/users")
@limiter.limit("120 per minute")
@admin_required
def list_users():
    """
    GET /api/v1/admin/users
    Paginated list of all users.
    """
    caller = _get_caller_admin()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str).strip()

    per_page = min(per_page, 100)

    query = User.query
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
            )
        )

    query = query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    users = []
    for u in pagination.items:
        d = u.to_dict()
        d["last_login"] = None
        users.append(d)

    record_audit_event(
        event_type="admin.view_users",
        actor_id=caller.id,
        actor_email=caller.email,
        actor_role=caller.role.value,
        details={"page": page, "search": search},
    )

    return jsonify({
        "users": users,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": per_page,
        "pages": pagination.pages,
    }), 200


@admin_bp.get("/users/<int:user_id>")
@limiter.limit("120 per minute")
@admin_required
def get_user(user_id):
    """
    GET /api/v1/admin/users/<id>
    Single user detail with cloud_accounts_count and scans_count.
    """
    caller = _get_caller_admin()
    user = db.get_or_404(User, user_id)
    data = user.to_dict()
    data["cloud_accounts_count"] = CloudAccount.query.filter_by(user_id=user.id).count()
    data["scans_count"] = ScanJob.query.filter_by(requested_by=user.id).count()

    record_audit_event(
        event_type="admin.view_user_detail",
        actor_id=caller.id,
        actor_email=caller.email,
        actor_role=caller.role.value,
        target_type="user",
        target_id=str(user.id),
    )

    return jsonify({"user": data}), 200


@admin_bp.patch("/users/<int:user_id>")
@limiter.limit("120 per minute")
@admin_required
def update_user(user_id):
    """
    PATCH /api/v1/admin/users/<id>
    Update role or is_active.
    Requires admin password re-entry for security confirmation.
    """
    caller = _get_caller_admin()
    user = db.get_or_404(User, user_id)
    data = request.get_json(silent=True) or {}

    role_change_requested = "role" in data
    status_change_requested = "is_active" in data

    if not role_change_requested and not status_change_requested:
        return jsonify({"message": "No changes requested.", "user": user.to_dict()}), 200

    # 1. Require password confirmation for security-sensitive modifications
    ok, err_msg = _verify_admin_password_confirmation(caller, data)
    if not ok:
        status_code = 429 if "locked" in (err_msg or "").lower() else 400
        return jsonify({"error": err_msg or "Admin password confirmation required."}), status_code

    # 2. Prevent self-demotion or self-suspension
    if user.id == caller.id:
        if role_change_requested and str(data["role"]).strip().lower() != RoleEnum.ADMIN.value:
            return jsonify({"error": "Administrators cannot demote their own account."}), 400
        if status_change_requested and not bool(data["is_active"]):
            return jsonify({"error": "Administrators cannot suspend their own account."}), 400

    # 3. Prevent removal of the last active administrator
    if user.is_admin():
        active_admin_count = User.query.filter_by(role=RoleEnum.ADMIN, is_active=True).count()
        if active_admin_count <= 1:
            if role_change_requested and str(data["role"]).strip().lower() != RoleEnum.ADMIN.value:
                return jsonify({"error": "Cannot demote the last active administrator."}), 400
            if status_change_requested and not bool(data["is_active"]):
                return jsonify({"error": "Cannot deactivate the last active administrator."}), 400

    previous_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    previous_active = user.is_active

    if role_change_requested:
        role_str = str(data["role"]).strip().lower()
        if role_str not in RoleEnum._value2member_map_:
            return jsonify({"error": f"Invalid role. Must be one of {list(RoleEnum._value2member_map_)}"}), 422
        user.role = RoleEnum(role_str)

    if status_change_requested:
        user.is_active = bool(data["is_active"])

    try:
        record_audit_event(
            event_type="user.update",
            actor_id=caller.id,
            actor_email=caller.email,
            actor_role=caller.role.value if hasattr(caller.role, "value") else str(caller.role),
            target_type="user",
            target_id=str(user.id),
            details={
                "previous_role": previous_role,
                "new_role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "previous_active": previous_active,
                "new_active": user.is_active,
            },
            session=db.session,
        )
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Admin user update transaction failed: %s", exc)
        return jsonify({"error": "Failed to update user. Transaction rolled back."}), 500

    # Revoke sessions/refresh tokens for affected user
    revoke_user_sessions(user.id)

    return jsonify({"message": "User updated.", "user": user.to_dict()}), 200


@admin_bp.delete("/users/<int:user_id>")
@limiter.limit("120 per minute")
@admin_required
def delete_user(user_id):
    """
    DELETE /api/v1/admin/users/<id>?confirm=true
    Delete user and cascade all related data.
    Requires ?confirm=true and admin password confirmation.
    """
    if request.args.get("confirm", "").lower() != "true":
        return jsonify({"error": "Add ?confirm=true to confirm deletion."}), 400

    caller = _get_caller_admin()
    user = db.get_or_404(User, user_id)
    data = request.get_json(silent=True) or {}

    # 1. Require password re-entry
    ok, err_msg = _verify_admin_password_confirmation(caller, data)
    if not ok:
        status_code = 429 if "locked" in (err_msg or "").lower() else 400
        return jsonify({"error": err_msg or "Admin password confirmation required for user deletion."}), status_code

    # 2. Prevent self-deletion
    if user.id == caller.id:
        return jsonify({"error": "Cannot delete your own account."}), 400

    # 3. Prevent removal of the last active administrator
    if user.is_admin():
        active_admin_count = User.query.filter_by(role=RoleEnum.ADMIN, is_active=True).count()
        if active_admin_count <= 1:
            return jsonify({"error": "Cannot delete the last active administrator."}), 400

    username = user.username
    target_id = user.id
    target_email = user.email

    # Revoke active sessions
    revoke_user_sessions(user.id)

    try:
        record_audit_event(
            event_type="user.delete",
            actor_id=caller.id,
            actor_email=caller.email,
            actor_role=caller.role.value if hasattr(caller.role, "value") else str(caller.role),
            target_type="user",
            target_id=str(target_id),
            details={"username": username, "email": target_email},
            session=db.session,
        )
        db.session.delete(user)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Admin user deletion transaction failed: %s", exc)
        return jsonify({"error": "Failed to delete user. Transaction rolled back."}), 500

    return jsonify({"message": f"User '{username}' and all related data deleted."}), 200


@admin_bp.post("/users/<int:user_id>/promote")
@limiter.limit("120 per minute")
@admin_required
def promote_user(user_id):
    """
    POST /api/v1/admin/users/<id>/promote
    Body: { "role": "admin"|"analyst"|"viewer", "admin_password": "..." }
    """
    caller = _get_caller_admin()
    user = db.get_or_404(User, user_id)
    data = request.get_json(silent=True) or {}
    role_str = str(data.get("role", "")).strip().lower()

    if role_str not in RoleEnum._value2member_map_:
        return jsonify({"error": f"Invalid role. Must be one of {list(RoleEnum._value2member_map_)}"}), 422

    # 1. Password confirmation
    ok, err_msg = _verify_admin_password_confirmation(caller, data)
    if not ok:
        status_code = 429 if "locked" in (err_msg or "").lower() else 400
        return jsonify({"error": err_msg or "Admin password confirmation required for role changes."}), status_code

    # 2. Prevent self-demotion
    if user.id == caller.id and role_str != RoleEnum.ADMIN.value:
        return jsonify({"error": "Administrators cannot demote their own account."}), 400

    # 3. Prevent demoting the last active administrator
    if user.is_admin() and role_str != RoleEnum.ADMIN.value:
        active_admin_count = User.query.filter_by(role=RoleEnum.ADMIN, is_active=True).count()
        if active_admin_count <= 1:
            return jsonify({"error": "Cannot demote the last active administrator."}), 400

    previous_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    user.role = RoleEnum(role_str)

    try:
        record_audit_event(
            event_type="user.role_change",
            actor_id=caller.id,
            actor_email=caller.email,
            actor_role=caller.role.value if hasattr(caller.role, "value") else str(caller.role),
            target_type="user",
            target_id=str(user.id),
            details={"previous_role": previous_role, "new_role": role_str},
            session=db.session,
        )
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Admin user promote transaction failed: %s", exc)
        return jsonify({"error": "Failed to update role. Transaction rolled back."}), 500

    # Revoke sessions for affected user
    revoke_user_sessions(user.id)

    return jsonify({
        "message": f"User '{user.username}' role changed to {role_str}.",
        "user": user.to_dict(),
    }), 200


# ═══════════════════════════════════════════════════════════════════════════════
#  AUDIT LOGS
# ═══════════════════════════════════════════════════════════════════════════════


@admin_bp.get("/audit-logs")
@limiter.limit("120 per minute")
@admin_required
def list_audit_logs():
    """
    GET /api/v1/admin/audit-logs
    Paginated timeline of immutable administrative & security events.
    """
    caller = _get_caller_admin()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    event_type = request.args.get("event_type", "").strip()

    query = AuditLog.query
    if event_type:
        query = query.filter_by(event_type=event_type)

    query = query.order_by(AuditLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    record_audit_event(
        event_type="admin.view_audit_logs",
        actor_id=caller.id,
        actor_email=caller.email,
        actor_role=caller.role.value,
        details={"page": page, "event_type": event_type},
    )

    return jsonify({
        "audit_logs": [log.to_dict() for log in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "per_page": per_page,
        "pages": pagination.pages,
    }), 200


# ═══════════════════════════════════════════════════════════════════════════════
#  PLATFORM OVERSIGHT
# ═══════════════════════════════════════════════════════════════════════════════


@admin_bp.get("/cloud-accounts")
@limiter.limit("120 per minute")
@admin_required
def list_all_cloud_accounts():
    """
    GET /api/v1/admin/cloud-accounts
    Every CloudAccount across all users — never exposes decrypted credentials.
    """
    caller = _get_caller_admin()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    provider = request.args.get("provider", "", type=str).strip().lower()
    status = request.args.get("status", "", type=str).strip().lower()

    query = CloudAccount.query
    if provider and provider in CloudProviderEnum._value2member_map_:
        query = query.filter_by(provider=CloudProviderEnum(provider))
    if status and status in AccountStatusEnum._value2member_map_:
        query = query.filter_by(status=AccountStatusEnum(status))

    query = query.order_by(CloudAccount.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    accounts = []
    for acc in pagination.items:
        d = acc.to_dict()
        owner = db.session.get(User, acc.user_id)
        d["username"] = owner.username if owner else "unknown"
        accounts.append(d)

    record_audit_event(
        event_type="admin.view_cloud_accounts",
        actor_id=caller.id,
        actor_email=caller.email,
        actor_role=caller.role.value,
        details={"page": page, "provider": provider},
    )

    return jsonify({
        "cloud_accounts": accounts,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": per_page,
        "pages": pagination.pages,
    }), 200


@admin_bp.get("/scans")
@limiter.limit("120 per minute")
@admin_required
def list_all_scans():
    """
    GET /api/v1/admin/scans
    Every ScanJob across all users.
    """
    caller = _get_caller_admin()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status = request.args.get("status", "", type=str).strip().lower()

    query = ScanJob.query
    if status and status in ScanStatusEnum._value2member_map_:
        query = query.filter_by(status=ScanStatusEnum(status))

    query = query.order_by(ScanJob.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    scans = []
    for scan in pagination.items:
        d = scan.to_dict()
        if scan.requested_by:
            owner = db.session.get(User, scan.requested_by)
            d["username"] = owner.username if owner else "unknown"
        else:
            d["username"] = "unknown"
        d["security_score"] = None
        d["total_findings"] = scan.result.total_findings if scan.result else None
        scans.append(d)

    record_audit_event(
        event_type="admin.view_scans",
        actor_id=caller.id,
        actor_email=caller.email,
        actor_role=caller.role.value,
        details={"page": page, "status": status},
    )

    return jsonify({
        "scans": scans,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": per_page,
        "pages": pagination.pages,
    }), 200


@admin_bp.get("/stats")
@limiter.limit("120 per minute")
@admin_required
def platform_stats():
    """
    GET /api/v1/admin/stats
    Aggregate platform metrics.
    """
    caller = _get_caller_admin()
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()

    accounts_by_provider = {}
    for provider in CloudProviderEnum:
        count = CloudAccount.query.filter_by(provider=provider).count()
        accounts_by_provider[provider.value] = count
    total_cloud_accounts = sum(accounts_by_provider.values())

    total_scans = ScanJob.query.count()
    completed_scans = ScanJob.query.filter_by(status=ScanStatusEnum.COMPLETED).count()
    failed_scans = ScanJob.query.filter_by(status=ScanStatusEnum.FAILED).count()

    from app.models.scan import Vulnerability
    total_recommendations = Vulnerability.query.count()

    total_savings_row = db.session.query(func.sum(CloudMetric.cost_usd)).scalar()
    total_estimated_savings = float(total_savings_row) if total_savings_row else 0.0

    error_accounts = CloudAccount.query.filter_by(status=AccountStatusEnum.ERROR).count()
    sync_error_rate = (error_accounts / total_cloud_accounts * 100) if total_cloud_accounts > 0 else 0.0

    record_audit_event(
        event_type="admin.view_stats",
        actor_id=caller.id,
        actor_email=caller.email,
        actor_role=caller.role.value,
    )

    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "total_cloud_accounts": total_cloud_accounts,
        "accounts_by_provider": accounts_by_provider,
        "total_scans": total_scans,
        "completed_scans": completed_scans,
        "failed_scans": failed_scans,
        "total_recommendations": total_recommendations,
        "total_estimated_savings": round(total_estimated_savings, 2),
        "sync_error_rate": round(sync_error_rate, 2),
    }), 200


# ═══════════════════════════════════════════════════════════════════════════════
#  SYSTEM HEALTH
# ═══════════════════════════════════════════════════════════════════════════════


@admin_bp.get("/system-health")
@limiter.limit("120 per minute")
@admin_required
def system_health():
    """
    GET /api/v1/admin/system-health
    Check connectivity to DB, Gemini API, Redis/Celery, and encryption key.
    """
    caller = _get_caller_admin()
    checks = {}

    # 1. Database
    try:
        db.session.execute(db.text("SELECT 1"))
        checks["database"] = {"status": "healthy", "message": "Connection OK"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "message": str(e)}

    # 2. Gemini API
    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            timeout = float(current_app.config.get("GEMINI_REQUEST_TIMEOUT_SECONDS", 10))
            with genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=timeout),
            ) as client:
                next(iter(client.models.list()), None)
            checks["gemini_api"] = {"status": "healthy", "message": "Reachable"}
        else:
            checks["gemini_api"] = {"status": "unhealthy", "message": "GEMINI_API_KEY not set"}
    except Exception as exc:
        checks["gemini_api"] = {
            "status": "unhealthy",
            "message": f"Provider check failed ({type(exc).__name__})",
        }

    # 3. Encryption key
    encryption_key = os.getenv("CLOUD_ENCRYPTION_KEY") or os.getenv("ENCRYPTION_KEY")
    if encryption_key:
        checks["encryption_key"] = {"status": "healthy", "message": "Encryption key configured"}
    else:
        checks["encryption_key"] = {"status": "unhealthy", "message": "Encryption key not set"}

    # 4. Redis / Celery
    try:
        from app.core.extensions import celery
        conn = celery.connection()
        conn.ensure_connection(max_retries=1, timeout=3)
        conn.close()
        checks["celery_redis"] = {"status": "healthy", "message": "Broker connection OK"}
    except Exception as e:
        checks["celery_redis"] = {"status": "unhealthy", "message": f"Broker unreachable: {str(e)}"}

    all_healthy = all(c["status"] == "healthy" for c in checks.values())

    record_audit_event(
        event_type="admin.view_system_health",
        actor_id=caller.id,
        actor_email=caller.email,
        actor_role=caller.role.value,
        details={"overall": "healthy" if all_healthy else "degraded"},
    )

    return jsonify({
        "overall": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }), 200
