"""Priority score service: wraps the AI PriorityEngine and persists results.

Uses the Overpass API (OpenStreetMap) to fetch REAL nearby hospitals,
schools, and road classifications for accurate proximity scoring.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.priority_engine import PriorityEngine
from app.models import (
    District,
    InfrastructureType,
    PriorityScore,
    Report,
    STATUS_REPORTED,
    STATUS_VERIFIED,
)
from app.services.geospatial_service import (
    get_location_context,
    get_nearest_hospital_distance,
    get_nearest_school_distance,
    get_nearest_road_class,
)


_priority_engine = PriorityEngine()


def _safe_loads(s: Optional[str], default: dict) -> dict:
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def compute_and_save_priority(
    db: Session,
    report: Report,
    ai_analyzer_used: bool = False,
    skip_overpass: bool = False,
) -> PriorityScore:
    """Compute a fresh PriorityScore for the report and persist it.

    Uses REAL geospatial data from Overpass API (OpenStreetMap) for:
      - nearest hospital distance (within 5 km)
      - nearest school distance (within 3 km)
      - nearest road class (within 200 m)

    Falls back to district-based estimates if Overpass is unavailable,
    OR if `skip_overpass=True` (used during seeding for speed).

    Results are cached per ~110m grid cell to avoid repeated API calls.
    """
    infra = db.get(InfrastructureType, report.infrastructure_type_id)
    district = db.get(District, report.district_id) if report.district_id else None

    # Severity preference: admin override > AI severity > None
    severity = report.final_severity or report.ai_severity

    # ---- REAL geospatial context from Overpass API ----
    # Skipped during seeding (skip_overpass=True) to avoid 25+ minute delays
    # from 60 demo reports × Overpass timeout.
    hospital_distance_km = None
    school_distance_km = None
    road_class = None

    if not skip_overpass:
        try:
            ctx = get_location_context(report.latitude, report.longitude)
            hospital_distance_km = ctx["nearest_hospital_km"]
            school_distance_km = ctx["nearest_school_km"]
            road_class = ctx["road_class"]
        except Exception as e:
            print(f"[priority_service] Overpass query failed, using fallback: {e}")

    # Fallback: district-based estimates (only if Overpass didn't return data)
    if hospital_distance_km is None and district:
        approx_radius_km = max(1.0, (district.area_sq_km or 100.0) ** 0.5) / 2.0
        hospital_distance_km = approx_radius_km * 0.6
    if school_distance_km is None and district:
        approx_radius_km = max(1.0, (district.area_sq_km or 100.0) ** 0.5) / 2.0
        school_distance_km = approx_radius_km * 0.4

    # Fallback: derive road class from infra type if Overpass didn't return one
    if road_class is None and infra:
        if infra.code.upper() in ("ROAD", "BRIDGE"):
            road_class = "major_road"
        elif infra.code.upper() == "TRAFFIC":
            road_class = "arterial"
        elif infra.code.upper() == "STREETLIGHT":
            road_class = "local"

    result = _priority_engine.compute(
        severity=severity,
        verification_count=report.verification_count or 0,
        population=district.population if district else None,
        road_class=road_class,
        hospital_distance_km=hospital_distance_km,
        school_distance_km=school_distance_km,
        infrastructure_code=infra.code if infra else None,
        created_at=report.created_at or datetime.utcnow(),
        status=report.status or STATUS_REPORTED,
        credibility_score=report.credibility_score or 0.0,
    )

    comps = result["components"]
    score = PriorityScore(
        report_id=report.id,
        score=result["score"],
        rank=None,
        severity_component=comps["severity_component"],
        verification_component=comps.get("verification_count_component", 0.0),
        population_component=comps.get("population_impact_component", 0.0),
        road_importance_component=comps.get("road_importance_component", 0.0),
        hospital_proximity_component=comps.get("hospital_proximity_component", 0.0),
        school_proximity_component=comps.get("school_proximity_component", 0.0),
        utility_importance_component=comps.get("utility_importance_component", 0.0),
        time_urgency_component=comps.get("time_urgency_component", 0.0),
        verification_status_component=comps.get("credibility_component", 0.0),
        recommended_response_time=result["recommended_response_time"],
        resource_urgency=result["resource_urgency"],
    )
    db.add(score)
    db.flush()
    return score


def recompute_all_priorities(db: Session) -> int:
    """Recompute priority scores for all open reports. Returns count.

    NOTE: This will call Overpass API for each report. For large numbers of
    reports, consider running this as a background job with rate limiting.
    """
    reports = db.execute(
        select(Report).where(Report.status.notin_(
            ["Resolved", "Rejected"]
        ))
    ).scalars().all()
    for r in reports:
        compute_and_save_priority(db, r)
    db.commit()
    return len(reports)
