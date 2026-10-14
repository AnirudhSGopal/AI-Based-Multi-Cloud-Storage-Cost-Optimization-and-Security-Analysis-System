from flask_jwt_extended import create_access_token

from app.core.extensions import db
from app.core.factory import create_app
from app.models.cloud import CloudProviderEnum
from app.models.cloud_account import CloudAccount
from app.models.user import RoleEnum, User


def test_user_cannot_read_or_delete_another_users_cloud_account():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        owner = User(username="account-owner", email="owner@example.test", role=RoleEnum.VIEWER)
        owner.password = "owner-password"
        attacker = User(
            username="account-attacker",
            email="attacker@example.test",
            role=RoleEnum.VIEWER,
        )
        attacker.password = "attacker-password"
        db.session.add_all([owner, attacker])
        db.session.flush()

        account = CloudAccount(
            user_id=owner.id,
            provider=CloudProviderEnum.AWS,
            account_label="Owner AWS",
            encrypted_credentials="not-used",
        )
        db.session.add(account)
        db.session.commit()
        account_id = account.id
        token = create_access_token(identity=str(attacker.id))

    headers = {"Authorization": f"Bearer {token}"}
    client = app.test_client()

    assert client.get(f"/api/v1/cloud/accounts/{account_id}", headers=headers).status_code == 404
    assert client.delete(
        f"/api/v1/cloud/accounts/{account_id}", headers=headers
    ).status_code == 404

    with app.app_context():
        assert db.session.get(CloudAccount, account_id) is not None
        db.session.remove()
        db.drop_all()
