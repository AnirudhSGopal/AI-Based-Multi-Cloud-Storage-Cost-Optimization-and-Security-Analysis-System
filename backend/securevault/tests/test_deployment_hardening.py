"""
Deployment hardening regression tests for CloudOpt production release.

Covers:
1. Cross-tenant isolation (IDOR) on cloud accounts, scans, sync, and delete.
2. Backdoor removal: login with old demo password creates or promotes nothing.
3. Production configuration: invalid cloud credentials fail with no demo data fallback.
4. Redis availability: broker failures fail fast/closed.
"""
import pytest
from flask_jwt_extended import create_access_token

from app.core.factory import create_app
from app.core.extensions import db
from app.models.user import User, RoleEnum
from app.models.cloud_account import CloudAccount
from app.models.cloud import CloudProviderEnum
from app.models.scan import ScanJob, ScanStatusEnum


@pytest.fixture
def hardening_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def hardening_client(hardening_app):
    return hardening_app.test_client()


def test_cross_tenant_isolation_matches_nonexistent_404(hardening_app, hardening_client):
    """
    Verify foreign tenant requests return 404 identical to non-existent resources.
    Tests cloud account get/sync, delete, scan get, and scan cancel.
    """
    with hardening_app.app_context():
        user_a = User(username="tenant_a", email="tenant_a@cloudopt.ai", role=RoleEnum.VIEWER)
        user_a.password = "TenantPassA123!"
        user_b = User(username="tenant_b", email="tenant_b@cloudopt.ai", role=RoleEnum.VIEWER)
        user_b.password = "TenantPassB123!"
        db.session.add_all([user_a, user_b])
        db.session.commit()

        # User A owns account and scan
        acc_a = CloudAccount(user_id=user_a.id, provider=CloudProviderEnum.AWS, account_label="Tenant A AWS")
        acc_a.set_credentials({"access_key_id": "AKIAUSERA", "secret_access_key": "secret", "region": "us-east-1"})
        scan_a = ScanJob(repo_url="https://github.com/acme/private-repo", requested_by=user_a.id, status=ScanStatusEnum.COMPLETED)
        db.session.add_all([acc_a, scan_a])
        db.session.commit()

        acc_a_id = acc_a.id
        scan_a_id = scan_a.id
        user_b_id = str(user_b.id)

    tok_b = create_access_token(identity=user_b_id, additional_claims={"aud": "customer", "role": "viewer"})
    headers_b = {"Authorization": f"Bearer {tok_b}"}

    # 1. Cloud Account GET (sync)
    res_foreign_acc = hardening_client.get(f"/api/v1/cloud/accounts/{acc_a_id}", headers=headers_b)
    res_none_acc = hardening_client.get("/api/v1/cloud/accounts/999999", headers=headers_b)
    assert res_foreign_acc.status_code == 404
    assert res_none_acc.status_code == 404

    # 2. Cloud Account DELETE
    res_foreign_del = hardening_client.delete(f"/api/v1/cloud/accounts/{acc_a_id}", headers=headers_b)
    res_none_del = hardening_client.delete("/api/v1/cloud/accounts/999999", headers=headers_b)
    assert res_foreign_del.status_code == 404
    assert res_none_del.status_code == 404

    # 3. Scan GET
    res_foreign_scan = hardening_client.get(f"/api/v1/scan/{scan_a_id}", headers=headers_b)
    res_none_scan = hardening_client.get("/api/v1/scan/999999", headers=headers_b)
    assert res_foreign_scan.status_code == 404
    assert res_none_scan.status_code == 404

    # 4. Scan DELETE (cancel)
    res_foreign_cancel = hardening_client.delete(f"/api/v1/scan/{scan_a_id}", headers=headers_b)
    res_none_cancel = hardening_client.delete("/api/v1/scan/999999", headers=headers_b)
    assert res_foreign_cancel.status_code == 404
    assert res_none_cancel.status_code == 404


def test_login_with_old_demo_password_creates_or_promotes_nothing(hardening_app, hardening_client):
    """
    Verify login with old hardcoded demo password fails and creates/promotes no users.
    """
    # Attempt login for non-existent demo identifier with backdoor password
    res = hardening_client.post(
        "/api/v1/auth/login",
        json={"email": "anirudhsgopal18@gmail.com", "password": "anirudh@123"},
    )
    assert res.status_code == 401
    assert "access_token" not in (res.get_json() or {})

    with hardening_app.app_context():
        # User must not be auto-provisioned
        u = User.query.filter_by(email="anirudhsgopal18@gmail.com").first()
        assert u is None


def test_production_bad_cloud_credentials_fails_with_no_demo_data(hardening_app, hardening_client):
    """
    Verify that in production mode, invalid credentials fail validation and never serve mock data.
    """
    hardening_app.config["ENABLE_DEMO_DATA"] = False

    with hardening_app.app_context():
        u = User(username="regular_cust", email="customer@example.com", role=RoleEnum.VIEWER)
        u.password = "CustPassword123!"
        db.session.add(u)
        db.session.commit()
        u_id = str(u.id)

    tok = create_access_token(identity=u_id, additional_claims={"aud": "customer", "role": "viewer"})

    res = hardening_client.post(
        "/api/v1/cloud/accounts/test",
        headers={"Authorization": f"Bearer {tok}"},
        json={
            "provider": "aws",
            "credentials": {"access_key_id": "AKIAINVALIDKEY1234", "secret_access_key": "badsecret", "region": "us-east-1"}
        }
    )
    # Should fail validation, never return 200 demo success
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False


def test_scan_start_fails_closed_when_broker_down(hardening_app, hardening_client, monkeypatch):
    """
    Verify scan queue fails fast and closed with HTTP 503 when Redis broker is unreachable.
    """
    with hardening_app.app_context():
        u = User(username="scan_user", email="scan_user@test.com", role=RoleEnum.VIEWER)
        u.password = "ScanPassword123!"
        db.session.add(u)
        db.session.commit()
        u_id = str(u.id)

    tok = create_access_token(identity=u_id, additional_claims={"aud": "customer", "role": "viewer"})
    headers = {"Authorization": f"Bearer {tok}"}

    # Simulate broker down
    monkeypatch.setattr("app.api.v1.scan.routes._broker_is_ready", lambda: False)

    res = hardening_client.post(
        "/api/v1/scan/start",
        headers=headers,
        json={"repo_url": "https://github.com/acme/sample-repo"}
    )
    assert res.status_code == 503
    assert "Scan queue unavailable" in res.get_json()["error"]
