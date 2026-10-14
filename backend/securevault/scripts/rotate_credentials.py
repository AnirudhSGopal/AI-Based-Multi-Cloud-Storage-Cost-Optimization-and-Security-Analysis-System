"""
Cloud Provider Credentials Re-Encryption CLI Utility.
Rotates all stored CloudAccount encrypted_credentials using MultiFernet.
Usage:
    python scripts/rotate_credentials.py --dry-run
    python scripts/rotate_credentials.py --commit
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.factory import create_app
from app.core.extensions import db
from app.models.cloud_account import CloudAccount
from app.utils.encryption import rotate_credential
from app.services.audit_logger import record_audit_event


def rotate_all_credentials(dry_run: bool = True) -> int:
    """Iterate through all CloudAccounts and re-encrypt credentials under primary key."""
    accounts = CloudAccount.query.all()
    total = len(accounts)
    print(f"[*] Found {total} cloud accounts to process (mode: {'DRY RUN' if dry_run else 'COMMIT'}).")

    rotated_count = 0
    errors = 0

    for acc in accounts:
        try:
            old_ciphertext = acc.encrypted_credentials
            new_ciphertext = rotate_credential(old_ciphertext)
            if old_ciphertext != new_ciphertext:
                rotated_count += 1
                if not dry_run:
                    acc.encrypted_credentials = new_ciphertext
        except Exception as exc:
            errors += 1
            print(f"[!] Error processing account {acc.id} (provider={acc.provider.value}): {exc}", file=sys.stderr)

    if not dry_run and rotated_count > 0:
        db.session.commit()
        record_audit_event(
            event_type="cloud.credentials_rotated",
            status="success",
            actor_role="system_cli",
            details={"total_accounts": total, "re_encrypted_count": rotated_count, "errors": errors},
        )
        print(f"[OK] Successfully committed re-encryption for {rotated_count}/{total} cloud accounts.")
    else:
        print(f"[*] Dry run complete: {rotated_count} accounts would be re-encrypted. {errors} errors.")

    return rotated_count


def main():
    parser = argparse.ArgumentParser(description="Rotate stored cloud credentials using MultiFernet primary key.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Simulate rotation without modifying the database.")
    group.add_argument("--commit", action="store_true", help="Apply and commit re-encrypted credentials to database.")

    args = parser.parse_args()

    app = create_app(os.getenv("FLASK_ENV", "production"))
    with app.app_context():
        rotate_all_credentials(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
