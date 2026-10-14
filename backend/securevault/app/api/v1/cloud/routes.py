"""
Cloud provider integration endpoints.

GET    /api/v1/cloud/accounts       – list connected cloud accounts
POST   /api/v1/cloud/accounts       – add or update a cloud account
POST   /api/v1/cloud/accounts/test  – dry-run test credentials
GET    /api/v1/cloud/accounts/<id>  – sync live cost/resources & get recommendations
DELETE /api/v1/cloud/accounts/<id>  – remove a cloud account
"""
import logging
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.core.extensions import db, limiter
from app.utils.decorators import active_user_required
from app.models.user import User
from app.models.cloud import CloudMetric, CloudProviderEnum
from app.models.cloud_account import CloudAccount, AccountStatusEnum
from app.services.cloud import get_provider_service
from app.services.cloud import optimizer

logger = logging.getLogger(__name__)

cloud_bp = Blueprint("cloud", __name__)


# ── 1. Dry-Run Test Connection Endpoint ──────────────────────────────────────

@cloud_bp.post("/accounts/test")
@cloud_bp.post("/test")
@jwt_required()
@limiter.limit("10 per minute")
@active_user_required
def test_cloud_credentials():
    """
    Test credentials without storing them.
    Expects body:
      { "provider": "aws"|"gcp"|"azure", "credentials": { ... } }
    """
    data = request.get_json(silent=True) or {}
    provider_str = (data.get("provider") or "").strip().lower()
    credentials = data.get("credentials") or {}

    if not provider_str or provider_str not in ("aws", "gcp", "azure"):
        return jsonify({"success": False, "error": "Provider must be 'aws', 'gcp', or 'azure'"}), 400

    if not credentials or not isinstance(credentials, dict):
        return jsonify({"success": False, "error": "Credentials object is required"}), 400

    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    from app.services.cloud.demo_dataset import is_demo_user
    if user and is_demo_user(user.email):
        return jsonify({
            "success": True,
            "message": f"{provider_str.upper()} credentials verified successfully.",
            "data": {"account_id": f"demo-{provider_str}-enterprise-01", "status": "active"}
        }), 200

    try:
        service = get_provider_service(provider_str)
        validation_res = _call_provider_validate(service, provider_str, credentials)

        if not validation_res.get("success"):
            return jsonify({
                "success": False,
                "error": validation_res.get("error", f"{provider_str.upper()} credential validation failed")
            }), 400

        return jsonify({
            "success": True,
            "message": f"{provider_str.upper()} credentials verified successfully.",
            "data": validation_res.get("data")
        }), 200

    except Exception as exc:
        logger.error(
            "Cloud credential test failed; exception_type=%s",
            type(exc).__name__,
        )
        return jsonify({"success": False, "error": "Cloud credential test failed."}), 500


from app.services.cloud.demo_dataset import (
    is_demo_user,
    get_demo_service_costs,
    get_demo_resources,
    get_demo_recommendations,
    get_30_day_chart_cycle,
)

# ── 2. List Connected Accounts ────────────────────────────────────────────────

@cloud_bp.get("/accounts")
@cloud_bp.get("/")
@jwt_required()
@limiter.limit("60 per minute")
@active_user_required
def list_cloud_accounts():
    """
    List all connected cloud accounts for the authenticated user.
    Credentials are NEVER returned in this response.
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    # Auto-seed demo accounts if demo user
    if user and is_demo_user(user.email):
        accounts = CloudAccount.query.filter_by(user_id=user_id).all()
        if len(accounts) < 3:
            from scripts.seed_demo_user import seed_demo_accounts_for_user
            seed_demo_accounts_for_user(user)
            accounts = CloudAccount.query.filter_by(user_id=user_id).all()
        return jsonify({
            "accounts": [acc.to_dict() for acc in accounts]
        }), 200

    accounts = CloudAccount.query.filter_by(user_id=user_id).all()
    return jsonify({
        "accounts": [acc.to_dict() for acc in accounts]
    }), 200


# ── 3. Add / Update Cloud Account ─────────────────────────────────────────────

@cloud_bp.post("/accounts")
@cloud_bp.post("/")
@jwt_required()
@limiter.limit("10 per hour")
@active_user_required
def add_cloud_account():
    """
    Validate and store (or update) cloud provider credentials.
    Expects body:
      { "provider": "aws"|"gcp"|"azure", "account_label": str, "credentials": { ... } }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    provider_str = (data.get("provider") or "").strip().lower()
    account_label = (data.get("account_label") or f"{provider_str.upper()} Account").strip()
    credentials = data.get("credentials") or {}

    if not provider_str or provider_str not in ("aws", "gcp", "azure"):
        return jsonify({"error": "Provider must be 'aws', 'gcp', or 'azure'"}), 400

    if not credentials or not isinstance(credentials, dict):
        return jsonify({"error": "Credentials object is required"}), 400

    provider_enum = CloudProviderEnum(provider_str)
    account = CloudAccount.query.filter_by(user_id=user_id, provider=provider_enum).first()

    final_creds = {**credentials}
    if account is not None:
        try:
            existing_creds = account.get_credentials()
            if isinstance(existing_creds, dict):
                # Merge incoming non-empty fields onto existing credentials
                merged = {**existing_creds}
                for k, v in credentials.items():
                    if v is not None and str(v).strip() != "":
                        merged[k] = v
                final_creds = merged
        except Exception as exc:
            logger.error(
                "Stored cloud credentials could not be decrypted; account_id=%s exception_type=%s",
                account.id,
                type(exc).__name__,
            )
            return jsonify({"error": "Stored cloud credentials could not be loaded."}), 500

    # 1. Validate merged credentials with live call (bypass for demo user)
    user = db.session.get(User, user_id)
    if not (user and is_demo_user(user.email)):
        try:
            service = get_provider_service(provider_str)
            validation_res = _call_provider_validate(service, provider_str, final_creds)

            if not validation_res.get("success"):
                return jsonify({
                    "error": validation_res.get("error", f"{provider_str.upper()} credential validation failed")
                }), 400
        except Exception as exc:
            logger.warning(
                "Cloud credential validation raised an error; exception_type=%s",
                type(exc).__name__,
            )
            return jsonify({"error": "Cloud credential validation failed."}), 400

    # 2. Store or update account record
    if account is None:
        account = CloudAccount(
            user_id=user_id,
            provider=provider_enum,
            account_label=account_label,
            status=AccountStatusEnum.CONNECTED
        )
        db.session.add(account)
    else:
        account.account_label = account_label
        account.status = AccountStatusEnum.CONNECTED

    # Encrypt and store merged credentials
    account.set_credentials(final_creds)
    db.session.commit()

    logger.info("Saved %s cloud account for user %s", provider_str, user_id)
    return jsonify({
        "message": f"{provider_str.upper()} account connected successfully.",
        "account": account.to_dict()
    }), 201


# ── 4. Sync Account & Get Live Cost/Resources/Recommendations ────────────────

@cloud_bp.get("/accounts/<int:account_id>")
@cloud_bp.get("/<int:account_id>")
@jwt_required()
@limiter.limit("120 per minute")
@active_user_required
def get_cloud_account(account_id: int):
    """
    Fetch live cost data & resource metadata for a specific account,
    run the AI cost optimizer, persist CloudMetrics, and return findings.
    """
    account = _get_account_or_404(account_id)
    provider_str = account.provider.value
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    from config.settings import get_provider_storage_capacity
    storage_size_gb = get_provider_storage_capacity(provider_str)

    # If demo user: serve curated mock data with 30-day reduction cycle
    if user and is_demo_user(user.email):
        cost_data = get_demo_service_costs(provider_str)
        resources = get_demo_resources(provider_str)
        recommendations = get_demo_recommendations()
        daily_trend = get_30_day_chart_cycle()

        account.last_synced_at = datetime.now(timezone.utc)
        account.status = AccountStatusEnum.CONNECTED
        _persist_metrics(account, cost_data, resources)
        db.session.commit()

        return jsonify({
            "account": account.to_dict(),
            "storage_size": storage_size_gb,
            "storage_size_gb": storage_size_gb,
            "cost_data": cost_data,
            "resources": resources,
            "recommendations": recommendations,
            "daily_trend": daily_trend,
            "cost_error": None,
        }), 200

    try:
        creds = account.get_credentials()
        service = get_provider_service(provider_str)

        # Fetch costs
        cost_res = _call_provider_cost(service, provider_str, creds)
        cost_data = cost_res.get("data", []) if cost_res.get("success") else []
        cost_error = cost_res.get("error") if not cost_res.get("success") else None

        # Fetch resources
        resource_res = _call_provider_resources(service, provider_str, creds)
        resources = resource_res.get("data", []) if resource_res.get("success") else []

        # Run AI-based cost optimizer with invariant storage capacity check
        provider_storage = {provider_str: storage_size_gb}
        recommendations = optimizer.analyze(
            resources,
            cost_data,
            provider_storage=provider_storage,
            user_id=user_id,
        )

        # Update account status and last_synced_at
        account.last_synced_at = datetime.now(timezone.utc)
        if cost_res.get("success") or resource_res.get("success"):
            account.status = AccountStatusEnum.CONNECTED
        else:
            account.status = AccountStatusEnum.ERROR

        # Persist CloudMetrics summary rows for historical stats
        _persist_metrics(account, cost_data, resources)
        db.session.commit()

        return jsonify({
            "account": account.to_dict(),
            "storage_size": storage_size_gb,
            "storage_size_gb": storage_size_gb,
            "cost_data": cost_data,
            "resources": resources,
            "recommendations": recommendations,
            "cost_error": cost_error,
            "resource_error": (
                resource_res.get("error") if not resource_res.get("success") else None
            ),
            "warnings": cost_res.get("warnings", []) + resource_res.get("warnings", []),
        }), 200

    except Exception as exc:
        db.session.rollback()
        logger.error(
            "Cloud account sync failed; account_id=%d exception_type=%s",
            account_id,
            type(exc).__name__,
        )
        account.status = AccountStatusEnum.ERROR
        try:
            db.session.commit()
        except Exception as persist_exc:
            db.session.rollback()
            logger.error(
                "Failed to persist cloud account error status; account_id=%d exception_type=%s",
                account_id,
                type(persist_exc).__name__,
            )
        return jsonify({"error": "Failed to sync cloud account."}), 500


# ── 4b. Multi-Cloud 30-Day Cost Trend Endpoint ───────────────────────────────

@cloud_bp.get("/chart-data")
@cloud_bp.get("/trend")
@jwt_required()
@limiter.limit("60 per minute")
@active_user_required
def get_chart_trend():
    """Return 30-day cost reduction trend cycle."""
    return jsonify({
        "trend": get_30_day_chart_cycle()
    }), 200


# ── 5. Delete Cloud Account ───────────────────────────────────────────────────

@cloud_bp.delete("/accounts/<int:account_id>")
@cloud_bp.delete("/<int:account_id>")
@jwt_required()
@limiter.limit("10 per hour")
@active_user_required
def delete_cloud_account(account_id: int):
    """
    Delete a connected cloud account and cascade-delete its metrics.
    """
    account = _get_account_or_404(account_id)
    provider_name = account.provider.value.upper()

    db.session.delete(account)
    db.session.commit()

    logger.info("Deleted %s account %d for user %s", provider_name, account_id, account.user_id)
    return jsonify({"message": f"{provider_name} account removed successfully."}), 200


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _get_account_or_404(account_id: int) -> CloudAccount:
    from flask import abort
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    account = db.session.get(CloudAccount, account_id)
    if account is None:
        abort(404)
    if not user.is_admin() and account.user_id != user_id:
        abort(404)
    return account


def _call_provider_validate(service, provider_str: str, creds: dict) -> dict:
    if provider_str == "aws":
        return service.validate_credentials(
            access_key_id=creds.get("access_key_id") or creds.get("aws_access_key_id"),
            secret_access_key=creds.get("secret_access_key") or creds.get("aws_secret_access_key"),
            region=creds.get("region") or creds.get("aws_region") or "us-east-1"
        )
    elif provider_str == "gcp":
        return service.validate_credentials(
            service_account_json=creds.get("service_account_json") or creds.get("gcp_sa_json"),
            project_id=creds.get("project_id") or creds.get("gcp_project_id")
        )
    elif provider_str == "azure":
        return service.validate_credentials(
            subscription_id=creds.get("subscription_id") or creds.get("azure_subscription_id"),
            tenant_id=creds.get("tenant_id") or creds.get("azure_tenant_id"),
            client_id=creds.get("client_id") or creds.get("azure_client_id"),
            client_secret=creds.get("client_secret") or creds.get("azure_client_secret")
        )
    return {"success": False, "error": "Unknown provider"}


def _call_provider_cost(service, provider_str: str, creds: dict) -> dict:
    if provider_str == "aws":
        return service.get_cost_data(
            access_key_id=creds.get("access_key_id") or creds.get("aws_access_key_id"),
            secret_access_key=creds.get("secret_access_key") or creds.get("aws_secret_access_key"),
            region=creds.get("region") or creds.get("aws_region") or "us-east-1"
        )
    elif provider_str == "gcp":
        return service.get_cost_data(
            service_account_json=creds.get("service_account_json") or creds.get("gcp_sa_json"),
            project_id=creds.get("project_id") or creds.get("gcp_project_id"),
            bigquery_dataset=creds.get("bigquery_dataset") or creds.get("gcp_dataset")
        )
    elif provider_str == "azure":
        return service.get_cost_data(
            subscription_id=creds.get("subscription_id") or creds.get("azure_subscription_id"),
            tenant_id=creds.get("tenant_id") or creds.get("azure_tenant_id"),
            client_id=creds.get("client_id") or creds.get("azure_client_id"),
            client_secret=creds.get("client_secret") or creds.get("azure_client_secret")
        )
    return {"success": False, "error": "Unknown provider"}


def _call_provider_resources(service, provider_str: str, creds: dict) -> dict:
    if provider_str == "aws":
        return service.get_resource_metadata(
            access_key_id=creds.get("access_key_id") or creds.get("aws_access_key_id"),
            secret_access_key=creds.get("secret_access_key") or creds.get("aws_secret_access_key"),
            region=creds.get("region") or creds.get("aws_region") or "us-east-1"
        )
    elif provider_str == "gcp":
        return service.get_resource_metadata(
            service_account_json=creds.get("service_account_json") or creds.get("gcp_sa_json"),
            project_id=creds.get("project_id") or creds.get("gcp_project_id")
        )
    elif provider_str == "azure":
        return service.get_resource_metadata(
            subscription_id=creds.get("subscription_id") or creds.get("azure_subscription_id"),
            tenant_id=creds.get("tenant_id") or creds.get("azure_tenant_id"),
            client_id=creds.get("client_id") or creds.get("azure_client_id"),
            client_secret=creds.get("client_secret") or creds.get("azure_client_secret")
        )
    return {"success": False, "error": "Unknown provider"}


def _persist_metrics(account: CloudAccount, cost_data: list, resources: list) -> None:
    """Save cost summary metrics into CloudMetric table."""
    try:
        db.session.query(CloudMetric).filter_by(
            cloud_account_id=account.id
        ).delete(synchronize_session=False)

        for item in cost_data:
            metric = CloudMetric(
                user_id=account.user_id,
                cloud_account_id=account.id,
                provider=account.provider,
                account_id=account.account_label,
                region="global",
                bucket_name=item.get("service"),
                storage_class="COST_SUMMARY",
                cost_usd=item.get("monthly_cost", 0.0),
            )
            db.session.add(metric)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error(
            "Failed to persist CloudMetrics for account %s (%s)",
            account.id,
            type(exc).__name__,
        )
        raise