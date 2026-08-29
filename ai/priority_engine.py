"""Severity Prioritization Engine.

Scoring model:
  - **Base score** comes from the AI-detected severity level (the dominant signal).
  - **Boosters** (geospatial, infrastructure, verification, time) are additive on
    top of the base — they can only raise the score, never drag it below the base.
  - Time urgency and verification count are supplementary boosters, not
    equal-weight factors. A brand-new report near a hospital and school
    should NOT score lower because nobody has verified it yet.

Signals → Score:
  Base:    severity (0–100)
  Boost:   hospital proximity, school proximity, road importance,
           utility importance, population impact,
           verification count, time urgency, credibility
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from ai.severity_classifier import SEVERITY_WEIGHTS

# ---------------------------------------------------------------------------
# Base score from severity
# ---------------------------------------------------------------------------
SEVERITY_BASE = {
    "Critical": 85,
    "High": 70,
    "Moderate": 50,
    "Low": 25,
    None: 40,  # unassessed → moderate starting point
}

# ---------------------------------------------------------------------------
# Booster configuration: (name, max_boost, description)
# Boosters are ADDITIVE on top of the base, capped so total ≤ 100.
# ---------------------------------------------------------------------------
BOOSTER_CONFIG = [
    ("hospital_proximity",  15, "Nearby hospital / clinic"),
    ("school_proximity",    10, "Nearby school / college"),
    ("population_impact",   10, "Population density"),
    ("road_importance",     10, "Road classification"),
    ("utility_importance",   8, "Infrastructure type importance"),
    ("verification_count",  10, "Community confirmations"),
    ("time_urgency",         5, "Report age"),
    ("credibility",          5, "Credibility score"),
]

MAX_TOTAL_BOOST = sum(max_b for _, max_b, _ in BOOSTER_CONFIG)  # 73


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def _normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def severity_to_base(severity: Optional[str]) -> float:
    """Map severity label to a base score 0–100."""
    return SEVERITY_BASE.get(severity, 40)


def _hospital_proximity_booster(distance_km: Optional[float], max_boost: float) -> float:
    """Closer to a hospital → bigger boost (critical infrastructure nearby)."""
    if distance_km is None:
        return max_boost * 0.4  # unknown → moderate assumption
    # 0 km → full boost, 5 km → zero boost
    ratio = max(0.0, 1.0 - (distance_km / 5.0))
    return max_boost * ratio


def _school_proximity_booster(distance_km: Optional[float], max_boost: float) -> float:
    if distance_km is None:
        return max_boost * 0.4
    # 0 km → full boost, 5 km → zero boost (consistent with hospital decay)
    ratio = max(0.0, 1.0 - (distance_km / 5.0))
    return max_boost * ratio


def _road_importance_booster(road_class: Optional[str], max_boost: float) -> float:
    mapping = {
        "highway": 1.0,
        "major_road": 0.85,
        "arterial": 0.7,
        "collector": 0.55,
        "local": 0.35,
        "residential": 0.25,
    }
    if not road_class:
        return max_boost * 0.5
    return max_boost * mapping.get(road_class.lower(), 0.5)


def _population_booster(population: Optional[int], max_boost: float) -> float:
    if not population:
        return max_boost * 0.4
    ratio = _normalize(float(population), 5000.0, 500_000.0)
    return max_boost * ratio


def _utility_importance_booster(infrastructure_code: Optional[str], max_boost: float) -> float:
    if not infrastructure_code:
        return max_boost * 0.5
    high = {"WATER", "POWER", "BRIDGE", "TRAFFIC", "HOSPITAL"}
    medium = {"ROAD", "DRAINAGE", "STREETLIGHT"}
    code = infrastructure_code.upper()
    if code in high:
        return max_boost
    if code in medium:
        return max_boost * 0.7
    return max_boost * 0.5


def _verification_count_booster(count: int, max_boost: float) -> float:
    """More citizen confirmations → higher boost. 0 confirmations → 0 boost."""
    if count <= 0:
        return 0.0
    ratio = _normalize(float(count), 1.0, 15.0)
    return max_boost * ratio


def _time_urgency_booster(created_at: datetime, now: datetime, max_boost: float) -> float:
    """Older unresolved reports get a small urgency boost."""
    hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
    if hours < 6:
        return 0.0  # very new → no urgency boost yet
    ratio = _normalize(hours, 6.0, 72.0)
    return max_boost * ratio


def _credibility_booster(credibility_score: float, max_boost: float) -> float:
    """Credibility score 0–10 → small boost."""
    ratio = min(1.0, credibility_score / 10.0)
    return max_boost * ratio


# Map booster names to their computation functions
_BOOSTER_FUNCS = {
    "hospital_proximity":  lambda val, mb: _hospital_proximity_booster(val, mb),
    "school_proximity":    lambda val, mb: _school_proximity_booster(val, mb),
    "population_impact":   lambda val, mb: _population_booster(val, mb),
    "road_importance":     lambda val, mb: _road_importance_booster(val, mb),
    "utility_importance":  lambda val, mb: _utility_importance_booster(val, mb),
    "verification_count":  lambda val, mb: _verification_count_booster(val, mb),
    "time_urgency":        lambda val, mb: _time_urgency_booster(*val, mb),
    "credibility":         lambda val, mb: _credibility_booster(val, mb),
}


class PriorityEngine:
    """Compute explainable priority scores using base + boosters model."""

    def compute(
        self,
        *,
        severity: Optional[str],
        verification_count: int = 0,
        population: Optional[int] = None,
        road_class: Optional[str] = None,
        hospital_distance_km: Optional[float] = None,
        school_distance_km: Optional[float] = None,
        infrastructure_code: Optional[str] = None,
        created_at: Optional[datetime] = None,
        status: str = "Reported",
        credibility_score: float = 0.0,
        now: Optional[datetime] = None,
    ) -> Dict:
        now = now or datetime.utcnow()
        if created_at is None:
            created_at = now

        # --- Base score from severity ---
        base_score = severity_to_base(severity)

        # --- Compute each booster ---
        raw_values = {
            "hospital_proximity":  hospital_distance_km,
            "school_proximity":    school_distance_km,
            "population_impact":   population,
            "road_importance":     road_class,
            "utility_importance":  infrastructure_code,
            "verification_count":  verification_count,
            "time_urgency":        (created_at, now),
            "credibility":         credibility_score,
        }

        boosters = {}
        total_boost = 0.0
        for name, max_boost, _desc in BOOSTER_CONFIG:
            raw_val = raw_values[name]
            fn = _BOOSTER_FUNCS[name]
            boost = round(fn(raw_val, max_boost), 4)
            boosters[name] = boost
            total_boost += boost

        # --- Final score: base + boosters, capped at 100 ---
        final_score = round(min(100.0, base_score + total_boost), 2)

        # --- Urgency tiers ---
        if final_score >= 80:
            urgency, response = "Immediate", "Within 2 hours"
        elif final_score >= 65:
            urgency, response = "High", "Within 6 hours"
        elif final_score >= 45:
            urgency, response = "Medium", "Within 24 hours"
        elif final_score >= 25:
            urgency, response = "Low", "Within 72 hours"
        else:
            urgency, response = "Minimal", "Within 7 days"

        # --- ML Model Prediction ---
        from ai.priority_ml_model import PriorityMLModel
        ml_model = PriorityMLModel()
        road_mapping = {"highway": 1.0, "major_road": 0.85, "arterial": 0.7, "collector": 0.55, "local": 0.35, "residential": 0.25}
        road_imp = road_mapping.get((road_class or "").lower(), 0.5)
        pop_imp = _normalize(float(population or 50000), 5000.0, 500000.0)
        infra_crits = {"WATER": 0.9, "POWER": 0.95, "BRIDGE": 0.9, "TRAFFIC": 0.85, "HOSPITAL": 1.0, "ROAD": 0.7, "DRAINAGE": 0.65}
        infra_crit = infra_crits.get((infrastructure_code or "").upper(), 0.5)
        hours_old = max(0.0, (now - created_at).total_seconds() / 3600.0)

        ml_result = ml_model.predict(
            severity_score=base_score,
            hospital_dist_km=hospital_distance_km,
            school_dist_km=school_distance_km,
            road_importance=road_imp,
            population_impact=pop_imp,
            infra_criticality=infra_crit,
            verification_count=verification_count,
            time_urgency_hours=hours_old,
        )

        # Build component dict for backward compatibility with the API / frontend
        components = {"severity_component": base_score / 100.0}
        for name, max_boost, _desc in BOOSTER_CONFIG:
            components[f"{name}_component"] = round(boosters[name] / max_boost, 4) if max_boost else 0.0

        return {
            "score": final_score,
            "ml_score": ml_result["ml_score"],
            "ml_model_used": ml_result["model_used"],
            "ml_confidence": ml_result["confidence"],
            "rank": None,
            "base_severity_score": base_score,
            "total_boost": round(total_boost, 2),
            "components": components,
            "boosters": boosters,
            "booster_descriptions": {name: desc for name, _, desc in BOOSTER_CONFIG},
            "recommended_response_time": response,
            "resource_urgency": urgency,
            "severity_input": severity,
            "computed_at": now.isoformat(),
        }

    @staticmethod
    def assign_ranks(scored_reports: list) -> list:
        """Assign 1-based ranks based on score (highest first)."""
        sorted_reports = sorted(scored_reports, key=lambda r: r["score"], reverse=True)
        for i, r in enumerate(sorted_reports, start=1):
            r["rank"] = i
        return sorted_reports
