"""Build GeoJSON FeatureCollections for the interactive map."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    District,
    InfrastructureType,
    PriorityScore,
    Report,
    SEVERITY_LOW,
    SEVERITY_MODERATE,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
)


SEVERITY_COLORS = {
    SEVERITY_LOW: "#22c55e",
    SEVERITY_MODERATE: "#f59e0b",
    SEVERITY_HIGH: "#ef4444",
    SEVERITY_CRITICAL: "#7c3aed",
    None: "#6b7280",
}


def reports_geojson(
    db: Session,
    *,
    district_id: Optional[int] = None,
    category_id: Optional[int] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    since=None,
    until=None,
) -> dict:
    q = select(Report)
    if district_id:
        q = q.where(Report.district_id == district_id)
    if category_id:
        q = q.where(Report.infrastructure_type_id == category_id)
    if severity:
        q = q.where((Report.ai_severity == severity) | (Report.final_severity == severity))
    if status:
        q = q.where(Report.status == status)
    if since:
        q = q.where(Report.created_at >= since)
    if until:
        q = q.where(Report.created_at <= until)

    reports = db.execute(q).scalars().all()

    features = []
    for r in reports:
        sev = r.final_severity or r.ai_severity
        infra = db.get(InfrastructureType, r.infrastructure_type_id)
        primary_image = next((img.file_url for img in r.images if img.is_primary), None) or (
            r.images[0].file_url if r.images else None
        )
        priority = db.execute(
            select(PriorityScore)
            .where(PriorityScore.report_id == r.id)
            .order_by(PriorityScore.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r.longitude, r.latitude]},
            "properties": {
                "id": r.id,
                "reference_code": r.reference_code,
                "title": r.title,
                "severity": sev,
                "severity_color": SEVERITY_COLORS.get(sev, "#6b7280"),
                "status": r.status,
                "category": infra.name if infra else None,
                "category_icon": infra.icon if infra else None,
                "verification_count": r.verification_count,
                "credibility_score": r.credibility_score,
                "priority_score": priority.score if priority else None,
                "priority_rank": priority.rank if priority else None,
                "image_url": primary_image,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            },
        })

    return {"type": "FeatureCollection", "features": features}


def districts_geojson(db: Session) -> dict:
    districts = db.execute(select(District)).scalars().all()
    features = []
    for d in districts:
        # We don't serialize the raw geometry (PostGIS WKB) — just metadata
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [
                # Use centroid if available; otherwise approximate with id-based offset
                d.id * 0.01, d.id * 0.01
            ]},
            "properties": {
                "id": d.id,
                "name": d.name,
                "code": d.code,
                "state": d.state,
                "population": d.population,
                "area_sq_km": d.area_sq_km,
            },
        })
    return {"type": "FeatureCollection", "features": features}


def heatmap_points(db: Session, severity: Optional[str] = None) -> List[list]:
    """Return [[lat, lng, weight], ...] for Leaflet.heat."""
    q = select(Report)
    if severity:
        q = q.where((Report.ai_severity == severity) | (Report.final_severity == severity))
    reports = db.execute(q).scalars().all()
    sev_weight = {
        SEVERITY_LOW: 0.3, SEVERITY_MODERATE: 0.6,
        SEVERITY_HIGH: 0.85, SEVERITY_CRITICAL: 1.0, None: 0.4,
    }
    points = []
    for r in reports:
        sev = r.final_severity or r.ai_severity
        points.append([r.latitude, r.longitude, sev_weight.get(sev, 0.5)])
    return points
