"""
Seed dummy cloud accounts and multi-cloud cost metrics for demo user
anirudhsgopal18@gmail.com into the Supabase database.
Security scans, scan jobs, and vulnerabilities are strictly kept real and NOT seeded.
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
from app.models.scan import ScanJob
from app.services.cloud.demo_dataset import get_demo_service_costs


def seed_dummy_data():
    app = create_app("development")
    with app.app_context():
        email = "anirudhsgopal18@gmail.com"
        user = User.query.filter_by(email=email).first()
        pwd = os.getenv("DEMO_USER_PASSWORD")
        if not pwd:
            import secrets
            pwd = secrets.token_urlsafe(16)
        if not user:
            user = User(
                username="anirudhsgopal18",
                email=email,
                role=RoleEnum.ANALYST,
                is_active=True,
            )
            user.password = pwd
            db.session.add(user)
            db.session.commit()
            print(f"[+] Created user {email}")
        else:
            if os.getenv("DEMO_USER_PASSWORD"):
                user.password = os.getenv("DEMO_USER_PASSWORD")
            user.role = RoleEnum.ANALYST
            user.is_active = True
            db.session.commit()
            print(f"[+] Verified user {email} (id={user.id})")

        # ── 1. Cloud Accounts & Metrics (Cost dummy data ONLY) ───────────────
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

            # Refresh CloudMetrics
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
        print("[+] Seeded AWS, GCP, and Azure accounts & cost metrics")

        # ── 2. Ensure Security scans are strictly REAL (clean up any dummy scan jobs) ──
        dummy_repo_urls = [
            "workspace://test-files",
            "https://github.com/AnirudhSGopal/maven-project",
            "https://github.com/AnirudhSGopal/myintern",
        ]
        dummy_jobs = ScanJob.query.filter(
            ScanJob.requested_by == user.id,
            ScanJob.repo_url.in_(dummy_repo_urls)
        ).all()
        for j in dummy_jobs:
            db.session.delete(j)
        db.session.commit()

        print(f"[SUCCESS] Cost dummy data seeded for {email}. Security scans kept 100% real only.")


if __name__ == "__main__":
    seed_dummy_data()
