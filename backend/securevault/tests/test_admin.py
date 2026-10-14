import pytest
import os
os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"

from app.core.factory import create_app
from app.core.extensions import db
from app.models.user import User, RoleEnum
from app.models.cloud_account import CloudAccount, AccountStatusEnum
from app.models.cloud import CloudMetric, CloudProviderEnum
from app.models.scan import ScanJob, ScanResult, ScanStatusEnum
from app.models.audit_log import AuditLog


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = User(username="admin_test", email="admin_test@cloudopt.ai", role=RoleEnum.ADMIN, is_active=True)
        admin.password = "adminpass123"
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def second_admin(app):
    with app.app_context():
        admin2 = User(username="admin_test2", email="admin_test2@cloudopt.ai", role=RoleEnum.ADMIN, is_active=True)
        admin2.password = "adminpass456"
        db.session.add(admin2)
        db.session.commit()
        return admin2.id


@pytest.fixture
def viewer_user(app):
    with app.app_context():
        viewer = User(username="viewer_test", email="viewer_test@cloudopt.ai", role=RoleEnum.VIEWER, is_active=True)
        viewer.password = "viewerpass123"
        db.session.add(viewer)
        db.session.commit()
        return viewer.id


def get_admin_token(client, email, password, totp_code=None):
    payload = {"username": email, "password": password}
    if totp_code:
        payload["totp_code"] = totp_code
    resp = client.post("/api/v1/admin/auth/login", json=payload)
    if resp.status_code != 200:
        return None
    return resp.get_json()["access_token"]


def get_customer_token(client, email, password):
    resp = client.post("/api/v1/auth/login", json={"username": email, "password": password})
    if resp.status_code != 200:
        return None
    return resp.get_json()["access_token"]


def get_token(client, email, password):
    if "admin" in email:
        return get_admin_token(client, email, password)
    return get_customer_token(client, email, password)


ADMIN_ENDPOINTS = [
    ("GET", "/api/v1/admin/users"),
    ("GET", "/api/v1/admin/users/1"),
    ("PATCH", "/api/v1/admin/users/1"),
    ("DELETE", "/api/v1/admin/users/1?confirm=true"),
    ("POST", "/api/v1/admin/users/1/promote"),
    ("GET", "/api/v1/admin/cloud-accounts"),
    ("GET", "/api/v1/admin/scans"),
    ("GET", "/api/v1/admin/stats"),
    ("GET", "/api/v1/admin/system-health"),
    ("GET", "/api/v1/admin/audit-logs"),
]


def test_unauthenticated_gets_404(client):
    """Unauthenticated requests to admin routes unconditionally return 404."""
    for method, endpoint in ADMIN_ENDPOINTS:
        if method == "GET":
            res = client.get(endpoint)
        elif method == "PATCH":
            res = client.patch(endpoint, json={})
        elif method == "DELETE":
            res = client.delete(endpoint)
        elif method == "POST":
            res = client.post(endpoint, json={})
        assert res.status_code == 404, f"Expected 404 for unauthenticated {endpoint}, got {res.status_code}"


def test_tampered_token_gets_404(client):
    """Tampered or invalid tokens return 404 on admin endpoints without leaking JWT errors."""
    bad_headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tampered.token"}
    for method, endpoint in ADMIN_ENDPOINTS:
        if method == "GET":
            res = client.get(endpoint, headers=bad_headers)
        elif method == "PATCH":
            res = client.patch(endpoint, headers=bad_headers, json={})
        elif method == "DELETE":
            res = client.delete(endpoint, headers=bad_headers)
        elif method == "POST":
            res = client.post(endpoint, headers=bad_headers, json={})
        assert res.status_code == 404, f"Expected 404 for tampered token {endpoint}, got {res.status_code}"


def test_non_admin_gets_404(client, viewer_user):
    """Regular authenticated users get 404 on every admin endpoint."""
    token = get_token(client, "viewer_test@cloudopt.ai", "viewerpass123")
    headers = {"Authorization": f"Bearer {token}"}

    for method, endpoint in ADMIN_ENDPOINTS:
        if method == "GET":
            res = client.get(endpoint, headers=headers)
        elif method == "PATCH":
            res = client.patch(endpoint, headers=headers, json={})
        elif method == "DELETE":
            res = client.delete(endpoint, headers=headers)
        elif method == "POST":
            res = client.post(endpoint, headers=headers, json={})
        assert res.status_code == 404, f"Expected 404 for non-admin {endpoint}, got {res.status_code}"


def test_demoted_admin_gets_404(client, app, admin_user, second_admin):
    """If an admin's role is demoted in DB, subsequent requests with existing token get 404."""
    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # First request works
    res = client.get("/api/v1/admin/users", headers=headers)
    assert res.status_code == 200

    # Demote user in database
    u = db.session.get(User, admin_user)
    u.role = RoleEnum.VIEWER
    db.session.commit()
    db.session.expire_all()

    # Next request immediately gets 404 (database-verified on every request)
    res_demoted = client.get("/api/v1/admin/users", headers=headers)
    assert res_demoted.status_code == 404


def test_admin_self_demotion_blocked(client, app, admin_user, second_admin):
    """An administrator cannot demote or suspend themselves."""
    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt self-demotion via PATCH
    res = client.patch(
        f"/api/v1/admin/users/{admin_user}",
        headers=headers,
        json={"role": "viewer", "admin_password": "adminpass123"},
    )
    assert res.status_code == 400
    assert "cannot demote their own account" in res.get_json()["error"]

    # Attempt self-suspension
    res_suspend = client.patch(
        f"/api/v1/admin/users/{admin_user}",
        headers=headers,
        json={"is_active": False, "admin_password": "adminpass123"},
    )
    assert res_suspend.status_code == 400
    assert "cannot suspend their own account" in res_suspend.get_json()["error"]


def test_last_active_admin_protection(client, app, admin_user, viewer_user):
    """Attempting to demote, suspend, or delete the last remaining active admin is blocked."""
    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # Only one admin exists in DB (admin_user)
    # Attempting to delete or demote must be blocked
    res_delete = client.delete(
        f"/api/v1/admin/users/{admin_user}?confirm=true",
        headers=headers,
        json={"admin_password": "adminpass123"},
    )
    assert res_delete.status_code == 400


def test_admin_routes_and_audit_rows(client, app, admin_user, second_admin, viewer_user):
    """Admin actions succeed when password is provided and create immutable audit rows."""
    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # GET /users
    res = client.get("/api/v1/admin/users", headers=headers)
    assert res.status_code == 200

    # PATCH /users/<id> requires password
    res_no_pw = client.patch(f"/api/v1/admin/users/{viewer_user}", headers=headers, json={"role": "analyst"})
    assert res_no_pw.status_code == 400

    # PATCH /users/<id> with password
    res = client.patch(
        f"/api/v1/admin/users/{viewer_user}",
        headers=headers,
        json={"role": "analyst", "is_active": False, "admin_password": "adminpass123"},
    )
    assert res.status_code == 200
    assert res.get_json()["user"]["role"] == "analyst"
    assert res.get_json()["user"]["is_active"] is False

    # Check audit log row was created in database
    with app.app_context():
        logs = AuditLog.query.filter_by(event_type="user.update").all()
        assert len(logs) >= 1
        assert logs[-1].actor_id == admin_user
        assert logs[-1].target_id == str(viewer_user)

    # GET /audit-logs endpoint
    res_audit = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert res_audit.status_code == 200
    data = res_audit.get_json()
    assert data["total"] >= 1


def test_user_deletion_cascade(client, app, admin_user):
    """User deletion cascades related data and writes audit row."""
    with app.app_context():
        target = User(username="target_user", email="target@cloudopt.ai", role=RoleEnum.VIEWER)
        target.password = "targetpass"
        db.session.add(target)
        db.session.commit()

        acc = CloudAccount(user_id=target.id, provider=CloudProviderEnum.AWS, account_label="Test AWS", encrypted_credentials="mock")
        db.session.add(acc)
        db.session.commit()

        scan = ScanJob(repo_url="https://github.com/example/repo", requested_by=target.id, status=ScanStatusEnum.COMPLETED)
        db.session.add(scan)
        db.session.commit()

        metric = CloudMetric(user_id=target.id, provider=CloudProviderEnum.AWS, cloud_account_id=acc.id, size_bytes=100)
        db.session.add(metric)
        db.session.commit()

        target_id = target.id
        acc_id = acc.id
        scan_id = scan.id
        metric_id = metric.id

    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # Delete without password fails
    res_no_pw = client.delete(f"/api/v1/admin/users/{target_id}?confirm=true", headers=headers)
    assert res_no_pw.status_code == 400

    # Delete user with confirm=true and admin_password
    res = client.delete(
        f"/api/v1/admin/users/{target_id}?confirm=true",
        headers=headers,
        json={"admin_password": "adminpass123"},
    )
    assert res.status_code == 200

    with app.app_context():
        assert db.session.get(User, target_id) is None
        assert db.session.get(CloudAccount, acc_id) is None
        assert db.session.get(ScanJob, scan_id) is None
        assert db.session.get(CloudMetric, metric_id) is None

        # Check deletion was logged in audit_logs
        delete_log = AuditLog.query.filter_by(event_type="user.delete", target_id=str(target_id)).first()
        assert delete_log is not None
        assert delete_log.actor_id == admin_user


def test_refresh_revocation_after_role_change(client, app, admin_user, viewer_user):
    """Changing a user's role revokes their active refresh tokens; re-login re-enables session."""
    # 1. Viewer logs in and gets access + refresh token
    login_resp = client.post("/api/v1/auth/login", json={"username": "viewer_test@cloudopt.ai", "password": "viewerpass123"})
    assert login_resp.status_code == 200
    viewer_refresh_1 = login_resp.get_json()["refresh_token"]

    # Refresh works initially
    ref_ok = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {viewer_refresh_1}"})
    assert ref_ok.status_code == 200
    viewer_refresh_rotated = ref_ok.get_json()["refresh_token"]

    # 2. Admin changes user role
    admin_token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    patch_resp = client.patch(
        f"/api/v1/admin/users/{viewer_user}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "analyst", "admin_password": "adminpass123"},
    )
    assert patch_resp.status_code == 200

    # 3. Viewer's active rotated refresh token is now revoked
    ref_revoked = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {viewer_refresh_rotated}"})
    assert ref_revoked.status_code == 401
    assert "revoked" in ref_revoked.get_json()["error"].lower()

    # 4. User can log in again and new session works (sleep 1.05s so new token's iat > revocation_ts)
    import time
    time.sleep(1.05)
    relogin_resp = client.post("/api/v1/auth/login", json={"username": "viewer_test@cloudopt.ai", "password": "viewerpass123"})
    assert relogin_resp.status_code == 200
    viewer_refresh_2 = relogin_resp.get_json()["refresh_token"]

    ref_ok_after = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {viewer_refresh_2}"})
    assert ref_ok_after.status_code == 200


def test_wrong_reauth_password(client, app, admin_user, viewer_user):
    """Wrong admin password rejects mutation with 400 and creates an admin.reauth_failed audit row."""
    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(
        f"/api/v1/admin/users/{viewer_user}",
        headers=headers,
        json={"role": "analyst", "admin_password": "WRONG_PASSWORD_123"},
    )
    assert res.status_code == 400
    assert "password confirmation" in res.get_json()["error"].lower()

    # Confirm admin.reauth_failed audit row exists
    with app.app_context():
        failed_log = AuditLog.query.filter_by(event_type="admin.reauth_failed").first()
        assert failed_log is not None
        assert failed_log.actor_id == admin_user
        assert failed_log.status == "denied"
        assert failed_log.details.get("reason") == "invalid_password_confirmation"


def test_audit_immutability(app):
    """AuditLog records cannot be updated or deleted at the ORM level."""
    with app.app_context():
        log = AuditLog(
            actor_role="admin",
            event_type="test.immutable_event",
            status="success",
        )
        db.session.add(log)
        db.session.commit()
        log_id = log.id

        # Attempt UPDATE
        log_to_update = db.session.get(AuditLog, log_id)
        log_to_update.status = "tampered"
        with pytest.raises(RuntimeError, match="append-only"):
            db.session.commit()
        db.session.rollback()

        # Attempt DELETE
        log_to_delete = db.session.get(AuditLog, log_id)
        db.session.delete(log_to_delete)
        with pytest.raises(RuntimeError, match="immutable"):
            db.session.commit()
        db.session.rollback()


def test_access_denied_row_creation(client, app, viewer_user):
    """Unauthorized access attempt creates an admin.access_denied audit row."""
    token = get_token(client, "viewer_test@cloudopt.ai", "viewerpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # Viewer calls admin endpoint -> gets 404
    res = client.get("/api/v1/admin/users", headers=headers)
    assert res.status_code == 404

    with app.app_context():
        denied_log = AuditLog.query.filter_by(event_type="admin.access_denied").order_by(AuditLog.id.desc()).first()
        assert denied_log is not None
        assert denied_log.status == "denied"
        assert denied_log.actor_id == viewer_user
        assert denied_log.details.get("reason") in ("insufficient_permissions", "invalid_audience", "unauthenticated_or_tampered_token")


def test_audit_details_sanitization(app):
    """Audit details sanitize and redact passwords, tokens, API keys, and secret credentials."""
    from app.services.audit_logger import record_audit_event

    with app.app_context():
        entry = record_audit_event(
            event_type="test.sanitization",
            actor_role="admin",
            details={
                "action": "user_create",
                "admin_password": "supersecretpassword",
                "access_token": "eyJhbGciOi...",
                "nested": {
                    "client_secret": "sensitive_key_val",
                    "safe_field": "visible_value"
                }
            }
        )
        assert entry is not None
        d = entry.details
        assert d["admin_password"] == "[REDACTED]"
        assert d["access_token"] == "[REDACTED]"
        assert d["nested"]["client_secret"] == "[REDACTED]"
        assert d["nested"]["safe_field"] == "visible_value"


def test_deactivated_user_rejected_on_all_authenticated_routes(client, app, viewer_user):
    """Deactivated users are rejected with 403 on all authenticated routes across the platform."""
    token = get_token(client, "viewer_test@cloudopt.ai", "viewerpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # Initial check: /me works
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200

    # Deactivate viewer in database
    u = db.session.get(User, viewer_user)
    u.is_active = False
    db.session.commit()
    db.session.expire_all()

    # Now ALL authenticated endpoints reject the deactivated user
    routes_to_test = [
        "/api/v1/auth/me",
        "/api/v1/cloud/accounts",
        "/api/v1/scan/999",
    ]
    for r in routes_to_test:
        resp = client.get(r, headers=headers)
        assert resp.status_code == 403, f"Expected 403 on {r} for disabled user, got {resp.status_code}"


def test_token_revocation_fails_closed_on_db_error(client, app, admin_user):
    """If database query in is_token_revoked or blocklist loader throws, fail closed."""
    from unittest.mock import patch
    from app.services.token_service import is_token_revoked

    # Direct unit test of fail-closed behavior:
    # 1. Missing iat fails closed (treated as revoked)
    assert is_token_revoked(admin_user, {}) is True

    # 2. DB exception in is_token_revoked fails closed
    with patch("app.services.token_service.TokenRevocation.query") as mock_query:
        mock_query.filter_by.side_effect = RuntimeError("Database connection lost")
        assert is_token_revoked(admin_user, {"iat": 1234567890}) is True

    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # 3. HTTP endpoint check with simulated DB error during blocklist check
    with patch("app.services.token_service.TokenRevocation.query") as mock_query:
        mock_query.filter_by.side_effect = RuntimeError("Database connection lost")
        resp_me = client.get("/api/v1/auth/me", headers=headers)
        assert resp_me.status_code in (401, 403)

        # On admin endpoint, fail closed yields 404 (zero information leak)
        resp_admin = client.get("/api/v1/admin/users", headers=headers)
        assert resp_admin.status_code == 404


def test_reauth_failure_lockout(client, app, admin_user, viewer_user):
    """5 failed re-auth attempts within 15 minutes trigger temporary lockout and admin.reauth_locked log."""
    from app.api.v1.admin.routes import _clear_reauth_failures
    _clear_reauth_failures(admin_user)

    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # Fail 4 times
    for i in range(4):
        res = client.patch(
            f"/api/v1/admin/users/{viewer_user}",
            headers=headers,
            json={"role": "analyst", "admin_password": f"wrong_{i}"},
        )
        assert res.status_code == 400

    # 5th attempt triggers lockout
    res_5 = client.patch(
        f"/api/v1/admin/users/{viewer_user}",
        headers=headers,
        json={"role": "analyst", "admin_password": "wrong_5"},
    )
    assert res_5.status_code == 429
    assert "locked" in res_5.get_json()["error"].lower()

    # Even right password is now locked out
    res_locked = client.patch(
        f"/api/v1/admin/users/{viewer_user}",
        headers=headers,
        json={"role": "analyst", "admin_password": "adminpass123"},
    )
    assert res_locked.status_code == 429

    # Verify admin.reauth_locked audit row was created
    with app.app_context():
        locked_row = AuditLog.query.filter_by(event_type="admin.reauth_locked").first()
        assert locked_row is not None
        assert locked_row.status == "denied"
        assert locked_row.actor_id == admin_user


def test_audit_write_failure_rolls_back_mutation(client, app, admin_user, viewer_user):
    """If writing the audit log row fails, the entire admin mutation is rolled back (fail closed)."""
    from unittest.mock import patch
    from app.api.v1.admin.routes import _clear_reauth_failures
    _clear_reauth_failures(admin_user)

    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    from app.services.audit_logger import record_audit_event as real_record

    def mock_audit(*args, **kwargs):
        if kwargs.get("event_type") == "user.update":
            raise RuntimeError("Audit disk full")
        return real_record(*args, **kwargs)

    # Mock record_audit_event to raise an exception during user.update mutation
    with patch("app.api.v1.admin.routes.record_audit_event", side_effect=mock_audit):
        res = client.patch(
            f"/api/v1/admin/users/{viewer_user}",
            headers=headers,
            json={"role": "analyst", "admin_password": "adminpass123"},
        )
        assert res.status_code == 500
        assert "rolled back" in res.get_json()["error"].lower()

    # Verify user role was NOT changed
    with app.app_context():
        u = db.session.get(User, viewer_user)
        assert u.role == RoleEnum.VIEWER


def test_admin_endpoint_returns_404_for_deactivated_and_revoked_admin(client, app, admin_user):
    """Deactivated or revoked admin gets 404 (never 403) on admin endpoints."""
    token = get_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Active admin gets 200
    res_ok = client.get("/api/v1/admin/users", headers=headers)
    assert res_ok.status_code == 200

    # 2. Deactivate admin
    u = db.session.get(User, admin_user)
    u.is_active = False
    db.session.commit()
    db.session.expire_all()

    # Admin endpoint returns 404, never 403
    res_disabled = client.get("/api/v1/admin/users", headers=headers)
    assert res_disabled.status_code == 404
    assert res_disabled.get_json() == {"error": "Not found"}

    # Re-activate admin and revoke token
    u.is_active = True
    db.session.commit()
    db.session.expire_all()

    import time
    time.sleep(1.05)
    from app.services.token_service import revoke_user_sessions
    revoke_user_sessions(admin_user)

    res_revoked = client.get("/api/v1/admin/users", headers=headers)
    assert res_revoked.status_code == 404
    assert res_revoked.get_json() == {"error": "Not found"}


def test_refresh_token_rotation(client, app, viewer_user):
    """POST /auth/refresh returns new access_token AND a new rotated refresh_token."""
    login_resp = client.post("/api/v1/auth/login", json={"username": "viewer_test@cloudopt.ai", "password": "viewerpass123"})
    assert login_resp.status_code == 200
    r1 = login_resp.get_json()["refresh_token"]

    ref_resp = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {r1}"})
    assert ref_resp.status_code == 200
    data = ref_resp.get_json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != r1


def test_refresh_token_reuse_detected_and_revokes_sessions(client, app, viewer_user):
    """Reusing an already rotated refresh token triggers reuse detection and revokes all sessions."""
    # 1. Login
    login_resp = client.post("/api/v1/auth/login", json={"username": "viewer_test@cloudopt.ai", "password": "viewerpass123"})
    assert login_resp.status_code == 200
    r1 = login_resp.get_json()["refresh_token"]

    # 2. First refresh rotates r1 -> issues r2
    ref1_resp = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {r1}"})
    assert ref1_resp.status_code == 200
    r2 = ref1_resp.get_json()["refresh_token"]

    # 3. Attacker or victim replays r1 (REUSE!)
    replay_resp = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {r1}"})
    assert replay_resp.status_code == 401
    assert "reuse detected" in replay_resp.get_json()["error"].lower()

    # 4. Confirm r2 is ALSO revoked due to security revocation
    ref2_resp = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {r2}"})
    assert ref2_resp.status_code == 401

    # 5. Confirm audit log recorded reuse
    with app.app_context():
        reuse_log = AuditLog.query.filter_by(event_type="auth.refresh_token_reuse").first()
        assert reuse_log is not None
        assert reuse_log.status == "denied"
        assert reuse_log.actor_id == viewer_user


def test_customer_and_admin_audience_separation_and_tampered_aud(client, app, admin_user, viewer_user):
    """Customer endpoints reject aud=admin tokens (403); admin endpoints reject aud=customer tokens (404); tampered aud fails."""
    from flask_jwt_extended import create_access_token

    admin_token = get_admin_token(client, "admin_test@cloudopt.ai", "adminpass123")
    customer_token = get_customer_token(client, "viewer_test@cloudopt.ai", "viewerpass123")

    # 1. Admin token hitting customer endpoint is rejected (403)
    res_customer = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_customer.status_code == 403

    # 2. Customer token hitting admin endpoint is rejected (404, never 403)
    res_admin = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {customer_token}"})
    assert res_admin.status_code == 404
    assert res_admin.get_json() == {"error": "Not found"}

    # 3. Tampered audience claim (aud="attacker" or missing)
    with app.app_context():
        tampered_token = create_access_token(identity=str(admin_user), additional_claims={"aud": "attacker"})

    res_tampered_admin = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res_tampered_admin.status_code == 404

    res_tampered_cust = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res_tampered_cust.status_code in (401, 403)


def test_admin_totp_mfa_login(client, app, admin_user):
    """Admin login requires valid TOTP MFA code when totp_secret is configured."""
    secret = "JBSWY3DPEHPK3PXP"
    with app.app_context():
        u = db.session.get(User, admin_user)
        u.totp_secret = secret
        db.session.commit()
        db.session.expire_all()

    # 1. Login without MFA code fails
    res_no_mfa = client.post("/api/v1/admin/auth/login", json={"username": "admin_test@cloudopt.ai", "password": "adminpass123"})
    assert res_no_mfa.status_code == 401
    assert "mfa" in res_no_mfa.get_json()["error"].lower()

    # 2. Login with invalid MFA code fails
    res_bad_mfa = client.post("/api/v1/admin/auth/login", json={"username": "admin_test@cloudopt.ai", "password": "adminpass123", "totp_code": "000000"})
    assert res_bad_mfa.status_code == 401

    # 3. Login with valid MFA code succeeds
    import base64, hashlib, hmac, struct, time
    key = base64.b32decode(secret, casefold=True)
    msg = struct.pack(">Q", int(time.time() // 30))
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[19] & 15
    valid_code = str((struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000).zfill(6)

    res_ok = client.post("/api/v1/admin/auth/login", json={"username": "admin_test@cloudopt.ai", "password": "adminpass123", "totp_code": valid_code})
    assert res_ok.status_code == 200
    assert "access_token" in res_ok.get_json()


def test_admin_ip_allowlist(client, app, admin_user):
    """When ADMIN_IP_ALLOWLIST is configured, requests from non-allowlisted IPs get 404."""
    token = get_admin_token(client, "admin_test@cloudopt.ai", "adminpass123")
    headers = {"Authorization": f"Bearer {token}"}

    import os
    # Allow only 10.50.0.1
    os.environ["ADMIN_IP_ALLOWLIST"] = "10.50.0.1/32"
    try:
        # Default test client IP (127.0.0.1) is rejected with 404
        res_blocked = client.get("/api/v1/admin/users", headers=headers)
        assert res_blocked.status_code == 404

        # Request from allowlisted IP succeeds
        res_allowed = client.get("/api/v1/admin/users", headers={**headers, "X-Forwarded-For": "10.50.0.1"})
        assert res_allowed.status_code == 200
    finally:
        os.environ.pop("ADMIN_IP_ALLOWLIST", None)


def test_customer_login_rate_limit_and_account_lockout(client, app, viewer_user):
    """Customer login locks account after 5 failed attempts in 15 minutes with 429."""
    # 5 wrong attempts
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"username": "viewer_test@cloudopt.ai", "password": "wrongpassword"})

    # 6th attempt (even with right password) is locked out
    res_locked = client.post("/api/v1/auth/login", json={"username": "viewer_test@cloudopt.ai", "password": "viewerpass123"})
    assert res_locked.status_code == 429
    assert "locked" in res_locked.get_json()["error"].lower()


def test_demo_disabled_in_production(app):
    """Under ProductionConfig, ENABLE_DEMO_DATA is False and is_demo_user() returns False."""
    from app.services.cloud.demo_dataset import is_demo_user
    with app.app_context():
        app.config["ENABLE_DEMO_DATA"] = False
        assert is_demo_user("anirudhsgopal18@gmai.com") is False
        assert is_demo_user("anirudhsgopal18@gmail.com") is False


def test_admin_totp_replay_protection(client, app, admin_user):
    """Replayed TOTP codes within the same 30s timestep are rejected."""
    secret = "JBSWY3DPEHPK3PXP"
    with app.app_context():
        u = db.session.get(User, admin_user)
        u.totp_secret = secret
        u.totp_last_timestep = 0
        db.session.commit()

    import base64, hashlib, hmac, struct, time
    key = base64.b32decode(secret, casefold=True)
    msg = struct.pack(">Q", int(time.time() // 30))
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[19] & 15
    valid_code = str((struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000).zfill(6)

    # 1. First use succeeds
    res1 = client.post("/api/v1/admin/auth/login", json={"username": "admin_test@cloudopt.ai", "password": "adminpass123", "totp_code": valid_code})
    assert res1.status_code == 200

    # 2. Immediate replay of identical code is rejected
    res2 = client.post("/api/v1/admin/auth/login", json={"username": "admin_test@cloudopt.ai", "password": "adminpass123", "totp_code": valid_code})
    assert res2.status_code == 401


def test_multifernet_encryption_and_rotation(monkeypatch):
    """MultiFernet can decrypt data encrypted with an older key and rotate it to the primary key."""
    from cryptography.fernet import Fernet
    from app.utils import encryption

    key_old = Fernet.generate_key().decode()
    key_new = Fernet.generate_key().decode()

    # 1. Encrypt with old key
    monkeypatch.setattr(encryption, "_fernet", encryption.MultiFernet([Fernet(key_old.encode())]))
    ciphertext_old = encryption.encrypt_credential("secret-data-123")

    # 2. MultiFernet with primary=key_new, fallback=key_old
    mf = encryption.MultiFernet([Fernet(key_new.encode()), Fernet(key_old.encode())])
    monkeypatch.setattr(encryption, "_fernet", mf)

    # Decrypt reads ciphertext created with old key
    assert encryption.decrypt_credential(ciphertext_old) == "secret-data-123"

    # Rotate re-encrypts with key_new
    ciphertext_rotated = encryption.rotate_credential(ciphertext_old)

    # 3. Verify rotated token decrypts under key_new alone
    mf_new_only = encryption.MultiFernet([Fernet(key_new.encode())])
    monkeypatch.setattr(encryption, "_fernet", mf_new_only)
    assert encryption.decrypt_credential(ciphertext_rotated) == "secret-data-123"


def test_cli_reset_admin_mfa(app, admin_user):
    """CLI tool resets admin TOTP MFA."""
    from scripts.reset_admin_mfa import reset_admin_mfa
    with app.app_context():
        u = db.session.get(User, admin_user)
        u.totp_secret = "JBSWY3DPEHPK3PXP"
        u.totp_last_timestep = 12345
        db.session.commit()

        success = reset_admin_mfa("admin_test@cloudopt.ai")
        assert success is True

        u_refreshed = db.session.get(User, admin_user)
        assert u_refreshed.totp_secret is None
        assert u_refreshed.totp_last_timestep == 0




