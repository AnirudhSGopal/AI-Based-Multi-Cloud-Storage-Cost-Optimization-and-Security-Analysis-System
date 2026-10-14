"""
Administrative CLI tool to reset an admin user's TOTP MFA configuration.
Usage:
    python -m scripts.reset_admin_mfa --email admin@cloudopt.ai
    python scripts/reset_admin_mfa.py --email admin@cloudopt.ai
"""
import argparse
import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.factory import create_app
from app.core.extensions import db
from app.models.user import User
from app.services.audit_logger import record_audit_event


def reset_admin_mfa(email: str, force: bool = False) -> bool:
    """Programmatically reset TOTP MFA for the given admin user."""
    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user:
        print(f"Error: User with email '{email}' not found.", file=sys.stderr)
        return False

    if not user.is_admin():
        print(f"Error: User '{email}' is not an administrator.", file=sys.stderr)
        return False

    user.totp_secret = None
    user.totp_last_timestep = 0
    db.session.commit()

    record_audit_event(
        event_type="admin.mfa_reset",
        status="success",
        actor_id=user.id,
        actor_email=user.email,
        actor_role="admin",
        details={"reset_mechanism": "cli_tool", "target_user_id": user.id},
    )
    print(f"Success: TOTP MFA reset for admin '{user.email}'. Next login will require new MFA setup.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Reset TOTP MFA for an admin user.")
    parser.add_argument("--email", required=True, help="Email of the admin user to reset.")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt.")
    args = parser.parse_args()

    app = create_app(os.getenv("FLASK_ENV", "production"))
    with app.app_context():
        if not args.yes:
            confirm = input(f"Are you sure you want to reset MFA for admin '{args.email}'? (yes/no): ").strip().lower()
            if confirm not in ("yes", "y"):
                print("MFA reset aborted.")
                sys.exit(0)

        success = reset_admin_mfa(args.email, force=args.yes)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

