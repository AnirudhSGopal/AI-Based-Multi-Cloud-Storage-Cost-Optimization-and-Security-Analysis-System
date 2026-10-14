"""
Seed / ensure demo user in database with password anirudh@123 and connected AWS, GCP, Azure accounts.
Usage:
    python scripts/seed_demo_user.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.core.factory import create_app
from app.core.extensions import db
from app.models.user import User, RoleEnum
from app.models.cloud_account import CloudAccount, AccountStatusEnum
from app.models.cloud import CloudProviderEnum, CloudMetric
from app.services.cloud.demo_dataset import get_demo_service_costs


def seed_demo_accounts_for_user(user: User):
    """Ensure AWS, GCP, and Azure accounts exist for the user."""
    providers = [
        (CloudProviderEnum.AWS, "AWS Production Primary (us-east-1)", {"access_key_id": "AKIA9DEMOEXAMPLE9982", "region": "us-east-1"}),
        (CloudProviderEnum.GCP, "GCP Analytics & Data Platform", {"project_id": "cloudopt-enterprise-prod-01", "bigquery_dataset": "billing_export_prod"}),
        (CloudProviderEnum.AZURE, "Azure Corporate Workloads", {"subscription_id": "sub-8841-92fa-azure-prod", "tenant_id": "tenant-0041-99af"}),
    ]

    for provider_enum, label, creds in providers:
        account = CloudAccount.query.filter_by(user_id=user.id, provider=provider_enum).first()
        if not account:
            account = CloudAccount(
                user_id=user.id,
                provider=provider_enum,
                account_label=label,
                status=AccountStatusEnum.CONNECTED
            )
            account.set_credentials(creds)
            db.session.add(account)
            db.session.flush()
        else:
            account.account_label = label
            account.status = AccountStatusEnum.CONNECTED
            account.set_credentials(creds)

        # Seed CloudMetric entries
        CloudMetric.query.filter_by(cloud_account_id=account.id).delete()
        cost_items = get_demo_service_costs(provider_enum.value)
        for item in cost_items:
            m = CloudMetric(
                user_id=user.id,
                cloud_account_id=account.id,
                provider=provider_enum,
                account_id=label,
                region="global",
                bucket_name=item.get("service"),
                storage_class="COST_SUMMARY",
                cost_usd=item.get("monthly_cost", 0.0),
            )
            db.session.add(m)

    db.session.commit()
    print(f"[OK] Seeded AWS, GCP, and Azure accounts & metrics for user {user.email}")


def seed_user(email: str, username: str, password: str | None = None):
    if not password:
        password = os.getenv("DEMO_USER_PASSWORD")
        if not password:
            import secrets
            password = secrets.token_urlsafe(16)
            print(f"[*] Generated password for {email}: {password}")
    user = User.query.filter_by(email=email).first()
    if not user:
        # Check if username exists
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            username = f"{username}_{email.split('@')[0]}"

        user = User(
            username=username,
            email=email,
            role=RoleEnum.ANALYST,
            is_active=True,
        )
        user.password = password
        db.session.add(user)
        db.session.commit()
        print(f"[OK] Created demo user: {email} (id={user.id})")
    else:
        user.password = password
        user.role = RoleEnum.ANALYST
        user.is_active = True
        db.session.commit()
        print(f"[OK] Updated demo user: {email} (id={user.id})")

    seed_demo_accounts_for_user(user)
    return user


def main():
    app = create_app("development")
    with app.app_context():
        # Create user for both anirudhsgopal18@gmai.com and anirudhsgopal18@gmail.com
        seed_user("anirudhsgopal18@gmai.com", "anirudhsgopal18")
        seed_user("anirudhsgopal18@gmail.com", "anirudh_gmail")
        print("\nAll demo accounts and credentials are ready!")


if __name__ == "__main__":
    main()
