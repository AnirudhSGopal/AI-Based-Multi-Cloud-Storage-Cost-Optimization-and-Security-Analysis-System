"""
User model with role-based access control.
Roles: admin  > analyst  > viewer
"""
import enum
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from app.core.extensions import db


class RoleEnum(str, enum.Enum):
    ADMIN   = "admin"
    ANALYST = "analyst"
    VIEWER  = "viewer"


class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(64),  unique=True, nullable=False, index=True)
    email      = db.Column(db.String(120), unique=True, nullable=False, index=True)
    _password  = db.Column("password_hash", db.String(256), nullable=False)
    role       = db.Column(db.Enum(RoleEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=RoleEnum.VIEWER)
    is_active   = db.Column(db.Boolean, nullable=False, default=True)
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_last_timestep = db.Column(db.BigInteger, nullable=True, default=0)
    created_at  = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # ── Relationships ─────────────────────────────────────────────────────
    scan_jobs = db.relationship("ScanJob", back_populates="owner",
                                 lazy="dynamic", cascade="all, delete-orphan")
    cloud_accounts = db.relationship("CloudAccount", back_populates="owner",
                                     lazy="dynamic", cascade="all, delete-orphan")

    # ── Password helpers ──────────────────────────────────────────────────
    @property
    def password(self):
        raise AttributeError("password is write-only")

    @password.setter
    def password(self, plaintext: str):
        self._password = generate_password_hash(plaintext)

    def verify_password(self, plaintext: str) -> bool:
        return check_password_hash(self._password, plaintext)

    # ── TOTP MFA (RFC 6238 standard library implementation with replay prevention) ──
    def verify_totp(self, code: str, window: int = 1) -> bool:
        """Verify 6-digit TOTP code against user's secret, rejecting replayed timesteps."""
        if not self.totp_secret or not code:
            return False
        import base64, hashlib, hmac, struct, time
        try:
            key = base64.b32decode(self.totp_secret.strip().upper(), casefold=True)
            step = int(time.time() // 30)
            for offset in range(-window, window + 1):
                cur_step = step + offset
                msg = struct.pack(">Q", cur_step)
                h = hmac.new(key, msg, hashlib.sha1).digest()
                offset_idx = h[19] & 15
                code_int = (struct.unpack(">I", h[offset_idx:offset_idx + 4])[0] & 0x7fffffff) % 1000000
                calc = str(code_int).zfill(6)
                if hmac.compare_digest(calc, str(code).strip()):
                    if self.totp_last_timestep and cur_step <= self.totp_last_timestep:
                        logger.warning("Replayed TOTP token rejected for user_id=%s timestep=%d", self.id, cur_step)
                        return False
                    self.totp_last_timestep = cur_step
                    return True
        except Exception:
            pass
        return False

    # ── RBAC helpers ──────────────────────────────────────────────────────
    def has_role(self, *roles: RoleEnum) -> bool:
        return self.role in roles

    def is_admin(self) -> bool:
        return self.role == RoleEnum.ADMIN

    def is_analyst_or_above(self) -> bool:
        return self.role in (RoleEnum.ADMIN, RoleEnum.ANALYST)

    # ── Serialisation ─────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        r_val = self.role.value if isinstance(self.role, RoleEnum) else str(self.role)
        from app.services.cloud.demo_dataset import is_demo_user
        return {
            "id":         self.id,
            "username":   self.username,
            "email":      self.email,
            "role":       r_val.lower(),
            "is_active":  self.is_active,
            "is_demo":    is_demo_user(self.email),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.username!r} role={self.role.value}>"