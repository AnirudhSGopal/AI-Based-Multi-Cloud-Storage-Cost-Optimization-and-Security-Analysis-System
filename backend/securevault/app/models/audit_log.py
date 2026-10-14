"""
AuditLog and TokenRevocation models.
AuditLog is strictly append-only (immutable).
"""
from datetime import datetime, timezone
from sqlalchemy import event

from app.core.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id           = db.Column(db.Integer, primary_key=True)
    actor_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email  = db.Column(db.String(120), nullable=True, index=True)
    actor_role   = db.Column(db.String(32), nullable=False, default="unknown")
    event_type   = db.Column(db.String(64), nullable=False, index=True)
    target_type  = db.Column(db.String(64), nullable=True)
    target_id    = db.Column(db.String(64), nullable=True)
    ip_address   = db.Column(db.String(45), nullable=True, index=True)
    user_agent   = db.Column(db.String(256), nullable=True)
    status       = db.Column(db.String(20), nullable=False, default="success")
    details      = db.Column(db.JSON, nullable=True)
    created_at   = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    actor = db.relationship("User", foreign_keys=[actor_id], lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "actor_email": self.actor_email,
            "actor_role": self.actor_role,
            "event_type": self.event_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status,
            "details": self.details or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Immutability enforcement at ORM level: prevent update and delete
@event.listens_for(AuditLog, "before_update")
def _prevent_audit_log_update(mapper, connection, target):
    raise RuntimeError("AuditLog records are append-only and cannot be modified.")


@event.listens_for(AuditLog, "before_delete")
def _prevent_audit_log_delete(mapper, connection, target):
    raise RuntimeError("AuditLog records are immutable and cannot be deleted.")


class TokenRevocation(db.Model):
    __tablename__ = "token_revocations"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class UsedRefreshToken(db.Model):
    """Tracks rotated refresh token JTIs to detect and reject token reuse."""
    __tablename__ = "used_refresh_tokens"

    id         = db.Column(db.Integer, primary_key=True)
    jti        = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


