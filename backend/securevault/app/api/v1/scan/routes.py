"""
Authenticated repository security scan endpoints.

POST   /api/v1/scan/start       – enqueue a repository scan
GET    /api/v1/scan/<job_id>    – get owned scan status and findings
DELETE /api/v1/scan/<job_id>    – cancel an owned queued scan
"""
import logging

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from redis import Redis
from sqlalchemy import select, update

from app.core.extensions import celery, db, limiter
from app.models.scan import ScanJob, ScanStatusEnum
from app.services.scanner.repo_cloner import CloneError, validate_branch, validate_repo_url
from app.tasks.scan_tasks import run_scan_task
from app.utils.decorators import active_user_required

scan_bp = Blueprint("scan", __name__)
logger = logging.getLogger(__name__)


@scan_bp.post("/start")
@jwt_required()
@active_user_required
@limiter.limit("5 per hour")
def start_scan():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required."}), 400

    gemini_review = data.get("gemini_review", False)
    if not isinstance(gemini_review, bool):
        return jsonify({"error": "gemini_review must be a boolean."}), 400

    try:
        repo_url = validate_repo_url(data.get("repo_url", data.get("repoUrl")))
        branch = validate_branch(data.get("branch", "main"))
    except CloneError as exc:
        return jsonify({"error": str(exc)}), 422

    if not _broker_is_ready():
        return jsonify({
            "error": (
                "Scan queue unavailable. Confirm Redis and the Celery worker are "
                "running, then retry."
            )
        }), 503

    user_id = int(get_jwt_identity())
    job = ScanJob(
        repo_url=repo_url,
        branch=branch,
        requested_by=user_id,
        gemini_review_requested=gemini_review,
    )
    db.session.add(job)
    db.session.commit()

    try:
        task = run_scan_task.delay(job.id)
    except Exception as exc:
        job.status = ScanStatusEnum.FAILED
        job.error_msg = "Unable to queue the scan."
        db.session.commit()
        logger.error(
            "Unable to queue scan job_id=%d; exception_type=%s",
            job.id,
            type(exc).__name__,
        )
        return jsonify({
            "error": (
                "Scan queue unavailable. Confirm Redis and the Celery worker are "
                "running, then retry."
            )
        }), 503

    job.celery_task_id = task.id
    db.session.commit()
    return jsonify({"scan": job.to_dict()}), 202


@scan_bp.get("/latest")
@jwt_required()
@active_user_required
def get_latest_scan():
    user_id = int(get_jwt_identity())
    job = (
        ScanJob.query.filter_by(requested_by=user_id, status=ScanStatusEnum.COMPLETED)
        .order_by(ScanJob.created_at.desc())
        .first()
    )
    if job is None:
        return jsonify({"scan": None}), 200

    payload = {"scan": job.to_dict()}
    if job.result is not None:
        payload["result"] = job.result.to_dict()
        payload["findings"] = [finding.to_dict() for finding in job.vulnerabilities]
    return jsonify(payload), 200


@scan_bp.get("/<int:job_id>")
@jwt_required()
@active_user_required
def get_scan_status(job_id: int):
    job = _get_owned_job(job_id)
    if job is None:
        return jsonify({"error": "Scan not found."}), 404

    payload = {"scan": job.to_dict()}
    if job.result is not None:
        payload["result"] = job.result.to_dict()
        payload["findings"] = [finding.to_dict() for finding in job.vulnerabilities]
    return jsonify(payload), 200


@scan_bp.delete("/<int:job_id>")
@jwt_required()
@active_user_required
def cancel_scan(job_id: int):
    job = _get_owned_job(job_id)
    if job is None:
        return jsonify({"error": "Scan not found."}), 404

    cancellation = db.session.execute(
        update(ScanJob)
        .where(
            ScanJob.id == job_id,
            ScanJob.requested_by == int(get_jwt_identity()),
            ScanJob.status == ScanStatusEnum.PENDING,
        )
        .values(status=ScanStatusEnum.CANCELLED)
    )
    if cancellation.rowcount != 1:
        db.session.rollback()
        return jsonify({"error": "Only queued scans can be cancelled."}), 409
    db.session.commit()

    if job.celery_task_id:
        try:
            celery.control.revoke(job.celery_task_id)
        except Exception as exc:
            logger.error(
                "Scan cancellation persisted but task revocation failed "
                "job_id=%d; exception_type=%s",
                job_id,
                type(exc).__name__,
            )
            db.session.refresh(job)
            return jsonify({
                "error": "Scan was cancelled, but task revocation could not be confirmed.",
                "scan": job.to_dict(),
            }), 503

    db.session.refresh(job)
    return jsonify({"scan": job.to_dict()}), 200


def _get_owned_job(job_id: int) -> ScanJob | None:
    user_id = int(get_jwt_identity())
    return db.session.execute(
        select(ScanJob).where(
            ScanJob.id == job_id,
            ScanJob.requested_by == user_id,
        )
    ).scalar_one_or_none()


def _broker_is_ready() -> bool:
    timeout = current_app.config["CELERY_BROKER_CONNECTION_TIMEOUT"]
    try:
        with Redis.from_url(
            current_app.config["CELERY_BROKER_URL"],
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
        ) as redis_client:
            return bool(redis_client.ping())
    except Exception as exc:
        logger.warning(
            "Scan broker check failed; exception_type=%s",
            type(exc).__name__,
        )
        return False
