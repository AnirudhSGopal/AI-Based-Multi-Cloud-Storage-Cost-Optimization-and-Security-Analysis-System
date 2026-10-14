"""
Token revocation tracking service.
Handles invalidation of active sessions/refresh tokens upon role change or deactivation.
"""
from datetime import datetime, timezone
import logging
from flask_jwt_extended import get_jwt

from app.core.extensions import db
from app.models.audit_log import TokenRevocation

logger = logging.getLogger(__name__)


def revoke_user_sessions(user_id: int) -> None:
    """Record session revocation timestamp for user in database and Redis."""
    now = datetime.now(timezone.utc)
    try:
        rev = TokenRevocation(user_id=user_id, revoked_at=now)
        db.session.add(rev)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to persist token revocation for user %s: %s", user_id, exc)


def is_token_revoked(user_id: int, jwt_payload: dict | None = None) -> bool:
    """
    Check if the token was issued prior to the user's most recent session revocation.
    Compares token's iat claim to the user's latest revoked_at timestamp in UTC.
    """
    try:
        payload = jwt_payload or get_jwt()
        token_iat = payload.get("iat")
        if not token_iat:
            # Fail closed: token without issued-at claim is treated as revoked
            return True

        latest_revocation = (
            TokenRevocation.query.filter_by(user_id=user_id)
            .order_by(TokenRevocation.revoked_at.desc())
            .first()
        )
        if latest_revocation:
            rev_dt = latest_revocation.revoked_at
            if rev_dt.tzinfo is None:
                rev_dt = rev_dt.replace(tzinfo=timezone.utc)
            revocation_ts = rev_dt.timestamp()

            # If token was issued before or at the moment of revocation, invalidate it
            if token_iat <= revocation_ts:
                return True
    except Exception as exc:
        logger.warning("Error checking token revocation; failing closed: %s", exc)
        return True
    return False
