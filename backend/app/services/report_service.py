"""Report service: create, list, fetch, verify, prioritize."""
from __future__ import annotations

import json
import os
import secrets
import time
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    AdminAction,
    District,
    Image,
    InfrastructureType,
    Notification,
    PriorityScore,
    Report,
    User,
    Verification,
    SEVERITY_LOW,
    SEVERITY_MODERATE,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
    STATUS_REPORTED,
    STATUS_VERIFIED,
    STATUS_ASSIGNED,
    STATUS_IN_PROGRESS,
    STATUS_RESOLVED,
    STATUS_REJECTED,
)
from app.schemas import (
    ReportCreate,
    ReportListItem,
    ReportOut,
    VerificationCreate,
)


# ---------- Helpers ----------
def _generate_reference_code() -> str:
    """Generate unique-ish human-friendly reference code: RPT-YYYYMMDD-XXXXXX"""
    today = datetime.utcnow().strftime("%Y%m%d")
    random_suffix = secrets.token_hex(3).upper()
    return f"RPT-{today}-{random_suffix}"


def _ensure_upload_dir() -> str:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    return settings.UPLOAD_DIR


async def _save_upload(file: UploadFile, prefix: str = "img") -> Tuple[str, str, int, str]:
    """Save an UploadFile to disk. Returns (file_path, file_url, size_bytes, mime_type)."""
    _ensure_upload_dir()
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file type: {ext}")

    mime = file.content_type or "image/jpeg"
    if mime not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported MIME: {mime}")

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds max size of {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    filename = f"{prefix}_{int(time.time() * 1000)}_{secrets.token_hex(4)}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/{filename}"
    return file_path, file_url, len(contents), mime


def _to_report_out(db: Session, report: Report) -> ReportOut:
    """Hydrate a Report ORM object into a fully-populated ReportOut."""
    infra = db.get(InfrastructureType, report.infrastructure_type_id)
    district = db.get(District, report.district_id) if report.district_id else None
    user = db.get(User, report.user_id)
    latest_priority = (
        db.execute(
            select(PriorityScore)
            .where(PriorityScore.report_id == report.id)
            .order_by(desc(PriorityScore.created_at))
            .limit(1)
        ).scalar_one_or_none()
    )

    images = report.images or []
    primary_image_url = next((img.file_url for img in images if img.is_primary), None) or (
        images[0].file_url if images else None
    )

    report_dict = {
        "id": report.id,
        "reference_code": report.reference_code,
        "title": report.title,
        "description": report.description,
        "address": report.address,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "category_id": report.infrastructure_type_id,
        "category_name": infra.name if infra else None,
        "district_id": report.district_id,
        "district_name": district.name if district else None,
        "ai_severity": report.ai_severity,
        "ai_confidence": report.ai_confidence,
        "ai_damage_type": report.ai_damage_type,
        "final_severity": report.final_severity,
        "status": report.status,
        "credibility_score": report.credibility_score,
        "verification_count": report.verification_count,
        "upvote_count": report.upvote_count,
        "downvote_count": report.downvote_count,
        "assigned_team": report.assigned_team,
        "resolution_notes": report.resolution_notes,
        "resolved_at": report.resolved_at,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "user_id": report.user_id,
        "user_name": user.full_name if user else None,
        "images": images,
        "priority": latest_priority,
        "verifications": report.verifications,
    }
    return ReportOut.model_validate(report_dict)


# ---------- Create ----------
def _run_ai_background(
    report_id: int,
    file_path: str,
    model_path: str,
) -> None:
    """Run AI severity analysis in a background thread.

    Creates its own DB session so it can safely outlive the request.
    """
    from app.core.database import SessionLocal
    from app.models import Report as ReportModel
    from ai.severity_classifier import SeverityAnalyzer
    import json as _json

    db = SessionLocal()
    try:
        report = db.get(ReportModel, report_id)
        if report is None:
            return

        analyzer = SeverityAnalyzer(
            model_path=model_path if model_path and os.path.exists(model_path) else None,
            use_ml=True,
            use_yolo=True,
        )
        ai_result = analyzer.analyze_image(file_path)
        if ai_result is None:
            return

        report.ai_severity = ai_result["severity"]
        report.ai_confidence = ai_result["confidence"]
        report.ai_damage_type = ai_result["damage_type"]
        ai_features_persist = {
            "features": ai_result.get("features", {}),
            "rule_based_severity": ai_result.get("rule_based_severity"),
            "ml_severity": ai_result.get("ml_severity"),
            "ml_confidence": ai_result.get("ml_confidence"),
            "yolo_severity_shift": ai_result.get("yolo_severity_shift"),
            "yolo_damage_types": ai_result.get("yolo_damage_types"),
            "yolo_detection_count": ai_result.get("yolo_detection_count"),
            "llm_severity": ai_result.get("llm_severity"),
            "llm_confidence": ai_result.get("llm_confidence"),
            "llm_description": ai_result.get("llm_description"),
            "llm_reasoning": ai_result.get("llm_reasoning"),
            "llm_model": ai_result.get("llm_model"),
        }
        report.ai_features = _json.dumps(ai_features_persist)
        db.commit()
        print(f"[reports] Background AI analysis done for report #{report_id}: severity={report.ai_severity}")
    except Exception as e:
        print(f"[reports] Background AI analysis failed for report #{report_id}: {e}")
        db.rollback()
    finally:
        db.close()


async def create_report(
    db: Session,
    user: User,
    payload: ReportCreate,
    images: List[UploadFile],
    ai_analyzer,
    background_tasks=None,
) -> ReportOut:
    # Validate infrastructure type
    infra = db.get(InfrastructureType, payload.category_id)
    if not infra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid infrastructure type.")

    # Determine district if not provided — match by point containment (best effort)
    district_id = payload.district_id
    if not district_id:
        district = db.execute(
            select(District).order_by(District.id).limit(1)
        ).scalar_one_or_none()
        district_id = district.id if district else None

    # Create report row
    report = Report(
        reference_code=_generate_reference_code(),
        user_id=user.id,
        district_id=district_id,
        infrastructure_type_id=infra.id,
        title=payload.title,
        description=payload.description,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        geom=f"SRID=4326;POINT({payload.longitude} {payload.latitude})",
        status=STATUS_REPORTED,
        credibility_score=1.0,
        final_severity=None,
    )
    db.add(report)
    db.flush()  # get report.id

    # Save images
    saved_image_path = None
    for idx, img_file in enumerate(images or []):
        try:
            file_path, file_url, size, mime = await _save_upload(img_file, prefix=f"rpt{report.id}")
        except HTTPException as e:
            db.rollback()
            raise e

        image_obj = Image(
            report_id=report.id,
            user_id=user.id,
            file_path=file_path,
            file_url=file_url,
            file_size_bytes=size,
            mime_type=mime,
            is_primary=(idx == 0),
        )
        db.add(image_obj)
        if idx == 0:
            saved_image_path = file_path

    db.flush()

    # Initial priority score (without AI data — recomputed after background analysis)
    from app.services.priority_service import compute_and_save_priority
    compute_and_save_priority(db, report, ai_analyzer_used=False)

    # Notify user
    db.add(Notification(
        user_id=user.id,
        report_id=report.id,
        title="Report submitted",
        message=f"Your report {report.reference_code} has been received and is being analyzed.",
        type="success",
    ))

    db.commit()
    db.refresh(report)

    # Schedule AI analysis as a background task (non-blocking)
    if saved_image_path is not None and background_tasks is not None:
        from app.core.config import settings
        background_tasks.add_task(
            _run_ai_background,
            report.id,
            saved_image_path,
            settings.AI_MODEL_PATH,
        )
        print(f"[reports] AI analysis scheduled in background for report #{report.id}")

    return _to_report_out(db, report)


# ---------- List / filter ----------
def list_reports(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    category_id: Optional[int] = None,
    district_id: Optional[int] = None,
    search: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    order_by: str = "created_at_desc",
) -> Tuple[List[ReportListItem], int]:
    q = select(Report)
    count_q = select(func.count(Report.id))

    if status_filter:
        q = q.where(Report.status == status_filter)
        count_q = count_q.where(Report.status == status_filter)
    if severity_filter:
        q = q.where((Report.ai_severity == severity_filter) | (Report.final_severity == severity_filter))
        count_q = count_q.where((Report.ai_severity == severity_filter) | (Report.final_severity == severity_filter))
    if category_id:
        q = q.where(Report.infrastructure_type_id == category_id)
        count_q = count_q.where(Report.infrastructure_type_id == category_id)
    if district_id:
        q = q.where(Report.district_id == district_id)
        count_q = count_q.where(Report.district_id == district_id)
    if search:
        like = f"%{search}%"
        q = q.where(Report.title.ilike(like) | Report.description.ilike(like) | Report.reference_code.ilike(like))
        count_q = count_q.where(Report.title.ilike(like) | Report.description.ilike(like) | Report.reference_code.ilike(like))
    if since:
        q = q.where(Report.created_at >= since)
        count_q = count_q.where(Report.created_at >= since)
    if until:
        q = q.where(Report.created_at <= until)
        count_q = count_q.where(Report.created_at <= until)

    # Ordering
    if order_by == "priority_desc":
        q = q.outerjoin(PriorityScore, PriorityScore.report_id == Report.id).order_by(desc(PriorityScore.score))
    elif order_by == "severity_desc":
        q = q.order_by(desc(Report.ai_severity))
    elif order_by == "created_at_asc":
        q = q.order_by(Report.created_at.asc())
    else:
        q = q.order_by(desc(Report.created_at))

    total = db.execute(count_q).scalar_one()
    offset = (page - 1) * page_size
    q = q.offset(offset).limit(page_size)
    reports = db.execute(q).scalars().all()

    items = []
    for r in reports:
        infra = db.get(InfrastructureType, r.infrastructure_type_id)
        district = db.get(District, r.district_id) if r.district_id else None
        primary_image = next((img.file_url for img in r.images if img.is_primary), None) or (
            r.images[0].file_url if r.images else None
        )
        priority = (
            db.execute(
                select(PriorityScore)
                .where(PriorityScore.report_id == r.id)
                .order_by(desc(PriorityScore.created_at))
                .limit(1)
            ).scalar_one_or_none()
        )
        items.append(ReportListItem(
            id=r.id,
            reference_code=r.reference_code,
            title=r.title,
            latitude=r.latitude,
            longitude=r.longitude,
            ai_severity=r.ai_severity,
            final_severity=r.final_severity,
            status=r.status,
            category_name=infra.name if infra else None,
            district_name=district.name if district else None,
            verification_count=r.verification_count,
            credibility_score=r.credibility_score,
            created_at=r.created_at,
            priority_score=priority.score if priority else None,
            priority_rank=priority.rank if priority else None,
            image_url=primary_image,
        ))
    return items, total


def get_report(db: Session, report_id: int) -> ReportOut:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return _to_report_out(db, report)


# ---------- Verification ----------
def add_verification(
    db: Session,
    report_id: int,
    user: User,
    payload: VerificationCreate,
    image: Optional[UploadFile] = None,
) -> ReportOut:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    if report.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot verify your own report.",
        )

    existing = db.execute(
        select(Verification).where(Verification.report_id == report_id, Verification.user_id == user.id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already verified this report.",
        )

    image_path = None
    if image is not None:
        file_path, file_url, _, _ = _save_upload_sync(image, prefix=f"ver{report_id}")
        image_path = file_url
        # Also attach as a secondary image
        db.add(Image(
            report_id=report.id,
            user_id=user.id,
            file_path=file_path,
            file_url=file_url,
            is_primary=False,
            caption=f"Verification by user #{user.id}",
        ))

    verification = Verification(
        report_id=report_id,
        user_id=user.id,
        severity_vote=payload.severity_vote,
        comment=payload.comment,
        is_confirmed=payload.is_confirmed,
        image_path=image_path,
    )
    db.add(verification)

    if payload.is_confirmed:
        report.upvote_count += 1
    else:
        report.downvote_count += 1
    report.verification_count += 1

    # Credibility: each verification adds 1.0 (capped at 10)
    report.credibility_score = min(10.0, report.credibility_score + 1.0)

    # If 3+ verifications and not verified → auto-mark Verified
    if report.verification_count >= 3 and report.status == STATUS_REPORTED:
        report.status = STATUS_VERIFIED
        db.add(Notification(
            user_id=report.user_id,
            report_id=report.id,
            title="Report verified",
            message=f"Your report {report.reference_code} has been verified by community consensus.",
            type="success",
        ))

    # Re-compute priority
    from app.services.priority_service import compute_and_save_priority
    compute_and_save_priority(db, report)

    # Notify owner
    db.add(Notification(
        user_id=report.user_id,
        report_id=report.id,
        title="New verification on your report",
        message=f"{user.full_name} {'confirmed' if payload.is_confirmed else 'flagged'} your report {report.reference_code}.",
        type="info",
    ))

    db.commit()
    db.refresh(report)
    return _to_report_out(db, report)


def _save_upload_sync(file: UploadFile, prefix: str = "img"):
    """Synchronous wrapper around UploadFile.read() (small files)."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_save_upload(file, prefix))


# ---------- Admin actions ----------
def update_status(
    db: Session, report_id: int, admin: User, new_status: str, notes: Optional[str] = None,
    assigned_team: Optional[str] = None,
) -> ReportOut:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    allowed = {
        STATUS_REPORTED, STATUS_VERIFIED, STATUS_REJECTED,
        STATUS_ASSIGNED, STATUS_IN_PROGRESS, STATUS_RESOLVED,
    }
    if new_status not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {new_status}")

    old = report.status
    report.status = new_status
    if assigned_team is not None:
        report.assigned_team = assigned_team
    if new_status == STATUS_RESOLVED:
        report.resolved_at = datetime.utcnow()
        if notes:
            report.resolution_notes = notes
    elif notes:
        report.resolution_notes = notes

    db.add(AdminAction(
        admin_id=admin.id, report_id=report.id, action="status_change",
        previous_value=old, new_value=new_status, notes=notes,
    ))
    db.add(Notification(
        user_id=report.user_id, report_id=report.id,
        title="Report status updated",
        message=f"Your report {report.reference_code} is now: {new_status}.",
        type="info",
    ))
    db.commit()
    db.refresh(report)
    return _to_report_out(db, report)


def update_severity(
    db: Session, report_id: int, admin: User, severity: str, notes: Optional[str] = None,
) -> ReportOut:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    allowed = {SEVERITY_LOW, SEVERITY_MODERATE, SEVERITY_HIGH, SEVERITY_CRITICAL}
    if severity not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid severity.")

    old = report.final_severity
    report.final_severity = severity
    db.add(AdminAction(
        admin_id=admin.id, report_id=report.id, action="severity_override",
        previous_value=old, new_value=severity, notes=notes,
    ))

    from app.services.priority_service import compute_and_save_priority
    compute_and_save_priority(db, report)
    db.commit()
    db.refresh(report)
    return _to_report_out(db, report)


def assign_team(db: Session, report_id: int, admin: User, team: str, notes: Optional[str] = None) -> ReportOut:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    old = report.assigned_team
    report.assigned_team = team
    if report.status in (STATUS_REPORTED, STATUS_VERIFIED):
        report.status = STATUS_ASSIGNED
    db.add(AdminAction(
        admin_id=admin.id, report_id=report.id, action="assign_team",
        previous_value=old, new_value=team, notes=notes,
    ))
    db.add(Notification(
        user_id=report.user_id, report_id=report.id,
        title="Response team assigned",
        message=f"Report {report.reference_code} has been assigned to: {team}.",
        type="info",
    ))
    db.commit()
    db.refresh(report)
    return _to_report_out(db, report)


def my_reports(db: Session, user_id: int) -> List[ReportOut]:
    reports = db.execute(
        select(Report).where(Report.user_id == user_id).order_by(desc(Report.created_at))
    ).scalars().all()
    return [_to_report_out(db, r) for r in reports]
