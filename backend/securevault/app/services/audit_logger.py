"""
Structured Audit Logger service.
Emits JSON structured logs and persists immutable audit records to the database.
Enforces automatic sanitization of sensitive keys (passwords, tokens, credentials).
"""
import json
import logging
from datetime import datetime, timezone
from flask import has_request_context, request

from app.core.extensions import db
from app.models.audit_log import AuditLog

logger = logging.getLogger("securevault.audit")
logger.setLevel(logging.INFO)

SENSITIVE_KEY_SUBSTRINGS = (
    "password", "secret", "token", "credential", "auth",
    "key", "body", "payload", "cookie"
)


def sanitize_audit_details(details: dict | None) -> dict:
    """Recursively redact passwords, tokens, API keys, and raw request bodies."""
    if not details or not isinstance(details, dict):
        return {}
    sanitized = {}
    for k, v in details.items():
        k_lower = str(k).lower()
        if any(substr in k_lower for substr in SENSITIVE_KEY_SUBSTRINGS):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_audit_details(v)
        elif isinstance(v, (list, tuple)):
            sanitized[k] = [
                sanitize_audit_details(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized


def get_real_client_ip() -> str:
    """Extract real client IP considering trusted reverse proxy headers."""
    if not has_request_context():
        return "127.0.0.1"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the leftmost client IP
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return request.remote_addr or "127.0.0.1"


def get_user_agent() -> str:
    if has_request_context():
        return request.headers.get("User-Agent", "")[:255]
    return ""


def record_audit_event(
    event_type: str,
    status: str = "success",
    actor_id: int | None = None,
    actor_email: str | None = None,
    actor_role: str = "unknown",
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    session=None,
) -> AuditLog | None:
    """
    Log an administrative or security event:
    1. Emits structured JSON log via logging.getLogger('securevault.audit').
    2. Persists immutable row to audit_logs table.
       - If session is passed, adds to the caller's session for atomic mutation commit.
       - If session is None, uses an independent Session(db.engine) connection so security
         events (e.g. access_denied, reauth_failed) never commit or rollback unrelated request state.
    """
    from sqlalchemy.orm import Session

    now = datetime.now(timezone.utc)
    ip = ip_address or get_real_client_ip()
    user_agent = get_user_agent()
    sanitized_details = sanitize_audit_details(details or {})

    # 1. Structured log emission
    log_payload = {
        "timestamp": now.isoformat(),
        "event_type": event_type,
        "status": status,
        "actor_id": actor_id,
        "actor_email": actor_email,
        "actor_role": actor_role,
        "target_type": target_type,
        "target_id": target_id,
        "ip_address": ip,
        "user_agent": user_agent,
        "details": sanitized_details,
    }
    logger.info(json.dumps(log_payload, default=str))

    log_entry = AuditLog(
        actor_id=actor_id,
        actor_email=actor_email,
        actor_role=actor_role or "unknown",
        event_type=event_type,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        ip_address=ip,
        user_agent=user_agent,
        status=status,
        details=sanitized_details,
        created_at=now,
    )

    # 2. Database persistence
    if session is not None:
        # Atomic with caller's transaction
        session.add(log_entry)
        return log_entry

    try:
        # Independent session/connection: does not touch or affect db.session
        with Session(db.engine, expire_on_commit=False) as isolated_session:
            isolated_session.add(log_entry)
            isolated_session.commit()
            return log_entry
    except Exception as exc:
        logger.error("Failed to commit isolated audit log entry to database: %s", exc)
        return None
