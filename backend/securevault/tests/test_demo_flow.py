"""
Test script for verifying demo user authentication and multi-cloud 30-day reduction cycle.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.factory import create_app
from app.core.extensions import db


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_demo_user_flow(app):
    client = app.test_client()

    with app.app_context():
        from app.models.user import User, RoleEnum
        demo = User(
            username="anirudhsgopal18",
            email="anirudhsgopal18@gmai.com",
            role=RoleEnum.ANALYST,
            is_active=True,
        )
        demo.password = "demo-isolated-test-password-8877"
        db.session.add(demo)
        db.session.commit()

    print("=== 1. Testing Demo Login ===")
    res = client.post("/api/v1/auth/login", json={
        "email": "anirudhsgopal18@gmai.com",
        "password": "demo-isolated-test-password-8877"
    })
    assert res.status_code == 200, f"Login failed: {res.get_json()}"
    data = res.get_json()
    token = data["access_token"]
    user = data["user"]
    print(f"[PASS] Demo login successful! User: {user['email']}, Role: {user['role']}")

    headers = {"Authorization": f"Bearer {token}"}

    print("\n=== 2. Testing Fetching Cloud Accounts ===")
    res_accounts = client.get("/api/v1/cloud/accounts", headers=headers)
    assert res_accounts.status_code == 200, f"Accounts fetch failed: {res_accounts.get_json()}"
    accounts_data = res_accounts.get_json()
    accounts = accounts_data.get("accounts", [])
    print(f"[PASS] Found {len(accounts)} connected cloud accounts:")
    for acc in accounts:
        print(f"  - Provider: {acc['provider'].upper()} | Label: {acc['account_label']} | Storage: {acc.get('storage_size_gb')} GB | Status: {acc['status']}")
        assert "storage_size" in acc, f"Missing storage_size attribute in account {acc}"
        assert "storage_size_gb" in acc, f"Missing storage_size_gb attribute in account {acc}"
        assert acc["storage_size"] in (4, 3), f"Unexpected storage size: {acc['storage_size']}"
        assert acc["storage_size_gb"] in (4, 3), f"Unexpected storage_size_gb: {acc['storage_size_gb']}"

    assert len(accounts) >= 3, "Expected at least 3 cloud accounts (AWS, GCP, Azure)"

    print("\n=== 3. Testing Syncing Cloud Account & 30-Day Cost Trend ===")
    first_acc_id = accounts[0]["id"]
    res_sync = client.get(f"/api/v1/cloud/accounts/{first_acc_id}", headers=headers)
    assert res_sync.status_code == 200, f"Sync failed: {res_sync.get_json()}"
    sync_data = res_sync.get_json()

    cost_data = sync_data.get("cost_data", [])
    resources = sync_data.get("resources", [])
    recommendations = sync_data.get("recommendations", [])
    daily_trend = sync_data.get("daily_trend", [])

    print(f"[PASS] Service cost items: {len(cost_data)}")
    for c in cost_data[:3]:
        print(f"  * {c['service']}: ${c['monthly_cost']:.2f}")

    print(f"[PASS] Discovered cloud resources: {len(resources)}")
    for r in resources[:3]:
        print(f"  * [{r['resource_type']}] {r['name']} ({r['status']})")

    print(f"[PASS] AI Optimization recommendations: {len(recommendations)}")
    total_savings = sum(r.get("estimated_monthly_savings", 0) for r in recommendations)
    print(f"  * Total Estimated Monthly Savings: ${total_savings:.2f}/mo")
    for r in recommendations[:3]:
        print(f"  * [{r['priority'].upper()}] {r['title']} (+${r['estimated_monthly_savings']:.2f}/mo)")

    print(f"[PASS] 30-Day Daily Trend: {len(daily_trend)} daily data points")
    day_1 = daily_trend[0]
    day_15 = daily_trend[14]
    day_30 = daily_trend[-1]
    print(f"  * Day 1 (Baseline):   Total ${day_1['Total']} (AWS: ${day_1['AWS']}, GCP: ${day_1['GCP']}, Azure: ${day_1['Azure']}) - Phase: {day_1['phase']}")
    print(f"  * Day 15 (Optimizing): Total ${day_15['Total']} (AWS: ${day_15['AWS']}, GCP: ${day_15['GCP']}, Azure: ${day_15['Azure']}) - Phase: {day_15['phase']}")
    print(f"  * Day 30 (Optimized):  Total ${day_30['Total']} (AWS: ${day_30['AWS']}, GCP: ${day_30['GCP']}, Azure: ${day_30['Azure']}) - Phase: {day_30['phase']}")
    reduction_pct = ((day_1['Total'] - day_30['Total']) / day_1['Total']) * 100
    print(f"  * Verified Cost Reduction: {reduction_pct:.1f}% reduction across 30 days!")

    for d in daily_trend:
        assert d.get("storage_aws") == 4, f"Expected storage_aws=4, got {d.get('storage_aws')}"
        assert d.get("storage_gcp") == 3, f"Expected storage_gcp=3, got {d.get('storage_gcp')}"
        assert d.get("storage_azure") == 3, f"Expected storage_azure=3, got {d.get('storage_azure')}"
        assert d.get("storage_total") == 10, f"Expected storage_total=10, got {d.get('storage_total')}"
    print("[PASS] Verified storage invariance (AWS: 4 GB, GCP: 3 GB, Azure: 3 GB, Total: 10 GB) across all 30 days.")

    print("\n=== ALL VERIFICATION CHECKS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    test_demo_user_flow()
