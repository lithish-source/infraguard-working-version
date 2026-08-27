"""Analytics service for the admin dashboard & analytics page."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    District,
    Image,
    InfrastructureType,
    PriorityScore,
    Report,
    User,
    Verification,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MODERATE,
    STATUS_REPORTED,
    STATUS_VERIFIED,
    STATUS_RESOLVED,
)
from app.schemas import (
    CategoryDistributionItem,
    DashboardSummary,
    DistrictAnalyticsItem,
    MonthlyTrendItem,
    SeverityDistributionItem,
)


SEVERITY_ORDER = [SEVERITY_LOW, SEVERITY_MODERATE, SEVERITY_HIGH, SEVERITY_CRITICAL]


def dashboard_summary(db: Session) -> DashboardSummary:
    total = db.execute(select(func.count(Report.id))).scalar_one()
    pending = db.execute(select(func.count(Report.id)).where(Report.status == STATUS_REPORTED)).scalar_one()
    verified = db.execute(select(func.count(Report.id)).where(Report.status == STATUS_VERIFIED)).scalar_one()
    resolved = db.execute(select(func.count(Report.id)).where(Report.status == STATUS_RESOLVED)).scalar_one()
    critical = db.execute(
        select(func.count(Report.id)).where(
            (Report.ai_severity == SEVERITY_CRITICAL) | (Report.final_severity == SEVERITY_CRITICAL)
        )
    ).scalar_one()
    users = db.execute(select(func.count(User.id))).scalar_one()
    verifications = db.execute(select(func.count(Verification.id))).scalar_one()

    # Avg response time (hours) = resolved_at - created_at for resolved reports
    avg_row = db.execute(
        select(
            func.avg(
                func.extract("epoch", Report.resolved_at - Report.created_at) / 3600.0
            )
        ).where(Report.status == STATUS_RESOLVED, Report.resolved_at.isnot(None))
    ).scalar_one()
    avg_response = float(avg_row) if avg_row else None
    response_rate = (resolved / total * 100.0) if total else 0.0

    return DashboardSummary(
        total_reports=total,
        pending_reports=pending,
        verified_reports=verified,
        resolved_reports=resolved,
        critical_incidents=critical,
        total_users=users,
        total_verifications=verifications,
        avg_response_time_hours=round(avg_response, 2) if avg_response else None,
        response_rate=round(response_rate, 2),
    )


def severity_distribution(db: Session) -> List[SeverityDistributionItem]:
    rows = db.execute(
        select(Report.ai_severity, func.count(Report.id)).group_by(Report.ai_severity)
    ).all()
    counts = {r[0] or "Unassessed": r[1] for r in rows}
    total = sum(counts.values()) or 1
    items = []
    for sev in SEVERITY_ORDER + ["Unassessed"]:
        c = counts.get(sev, 0)
        items.append(SeverityDistributionItem(
            severity=sev, count=c, percentage=round(c / total * 100.0, 2)
        ))
    return items


def category_distribution(db: Session) -> List[CategoryDistributionItem]:
    rows = db.execute(
        select(
            InfrastructureType.name,
            func.count(Report.id),
            func.count(Report.id).filter(
                (Report.ai_severity == SEVERITY_CRITICAL) | (Report.final_severity == SEVERITY_CRITICAL)
            ),
        )
        .join(Report, Report.infrastructure_type_id == InfrastructureType.id)
        .group_by(InfrastructureType.name)
    ).all()
    return [CategoryDistributionItem(category=r[0], count=r[1], critical_count=r[2]) for r in rows]


def monthly_trend(db: Session, months: int = 6) -> List[MonthlyTrendItem]:
    since = datetime.utcnow() - timedelta(days=months * 30)
    rows = db.execute(
        select(
            func.to_char(Report.created_at, "YYYY-MM"),
            func.count(Report.id),
            func.count(Report.id).filter(Report.status == STATUS_RESOLVED),
        )
        .where(Report.created_at >= since)
        .group_by(func.to_char(Report.created_at, "YYYY-MM"))
        .order_by(func.to_char(Report.created_at, "YYYY-MM"))
    ).all()
    return [MonthlyTrendItem(month=r[0], reports=r[1], resolved=r[2]) for r in rows]


def district_analytics(db: Session) -> List[DistrictAnalyticsItem]:
    rows = db.execute(
        select(
            District.name,
            func.count(Report.id),
            func.count(Report.id).filter(
                (Report.ai_severity == SEVERITY_CRITICAL) | (Report.final_severity == SEVERITY_CRITICAL)
            ),
            func.count(Report.id).filter(Report.status == STATUS_RESOLVED),
            func.avg(PriorityScore.score),
        )
        .join(Report, Report.district_id == District.id, isouter=True)
        .outerjoin(PriorityScore, PriorityScore.report_id == Report.id)
        .group_by(District.name)
    ).all()
    return [
        DistrictAnalyticsItem(
            district=r[0] or "Unknown",
            reports=r[1] or 0,
            critical=r[2] or 0,
            resolved=r[3] or 0,
            avg_priority=round(float(r[4]), 2) if r[4] else 0.0,
        )
        for r in rows
    ]


def response_time_analytics(db: Session) -> dict:
    rows = db.execute(
        select(
            func.avg(func.extract("epoch", Report.resolved_at - Report.created_at) / 3600.0),
            func.min(func.extract("epoch", Report.resolved_at - Report.created_at) / 3600.0),
            func.max(func.extract("epoch", Report.resolved_at - Report.created_at) / 3600.0),
        ).where(Report.status == STATUS_RESOLVED, Report.resolved_at.isnot(None))
    ).one()
    return {
        "avg_hours": round(float(rows[0]), 2) if rows[0] else None,
        "min_hours": round(float(rows[1]), 2) if rows[1] else None,
        "max_hours": round(float(rows[2]), 2) if rows[2] else None,
    }


def repeat_incidents(db: Session, threshold_km: float = 0.5) -> List[dict]:
    """Detect reports within threshold_km of each other for the same infra type."""
    reports = db.execute(
        select(Report).where(Report.status != "Rejected")
    ).scalars().all()
    clusters = []
    used = set()
    for i, r1 in enumerate(reports):
        if r1.id in used:
            continue
        group = [r1]
        for r2 in reports[i + 1:]:
            if r2.id in used or r2.infrastructure_type_id != r1.infrastructure_type_id:
                continue
            # Haversine approx
            d = _haversine(r1.latitude, r1.longitude, r2.latitude, r2.longitude)
            if d <= threshold_km:
                group.append(r2)
                used.add(r2.id)
        if len(group) > 1:
            clusters.append({
                "infrastructure_type_id": r1.infrastructure_type_id,
                "center": {"lat": r1.latitude, "lng": r1.longitude},
                "count": len(group),
                "report_ids": [r.id for r in group],
            })
            used.add(r1.id)
    return clusters


def _haversine(lat1, lon1, lat2, lon2) -> float:
    import math
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def citizen_participation(db: Session) -> dict:
    total_users = db.execute(select(func.count(User.id))).scalar_one()
    active_users = db.execute(
        select(func.count(func.distinct(Report.user_id)))
    ).scalar_one()
    verifiers = db.execute(select(func.count(func.distinct(Verification.user_id)))).scalar_one()
    avg_verifications_per_report = db.execute(
        select(func.avg(Report.verification_count))
    ).scalar_one()
    return {
        "total_citizens": total_users,
        "citizens_who_reported": active_users,
        "citizens_who_verified": verifiers,
        "avg_verifications_per_report": round(float(avg_verifications_per_report), 2)
        if avg_verifications_per_report else 0.0,
    }
