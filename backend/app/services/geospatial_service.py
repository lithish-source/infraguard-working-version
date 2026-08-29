"""Geospatial service: queries OpenStreetMap Overpass API for real nearby
hospitals, schools, and road classifications.

The Overpass API is free, requires no API key, and provides global OSM data.
We cache results per rounded lat/lng (~110m grid) to avoid repeated queries.

Rate limits: Be polite — max 1 request every 2 seconds is recommended.
The Overpass API will return 429 Too Many Requests if abused.
"""
from __future__ import annotations

import math
import time
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import httpx

# Cache TTL — results are cached for the lifetime of the process.
# For very long-running deployments, add a TTL via a timestamp check.

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# The Overpass API rejects requests with Python's default User-Agent.
# We must send a browser-like User-Agent to get 200 responses.
_OVERPASS_HEADERS = {
    "User-Agent": "InfraGuard/1.0 (infraguard-app; https://github.com/infraguard)",
    "Accept": "application/json",
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _round_coord(value: float, decimals: int = 3) -> float:
    """Round to ~110m grid (3 decimals) for cache keying."""
    return round(value, decimals)


def _run_overpass_query(query: str, timeout: float = 15.0, retries: int = 2) -> dict:
    """Execute an Overpass QL query, trying multiple endpoints with retry.

    Each endpoint is tried once; on 429 (rate limit) we back off and retry
    the same endpoint up to ``retries`` times before moving to the next.
    """
    payload = {"data": query}
    last_error = None
    for attempt in range(retries + 1):
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(endpoint, data=payload, headers=_OVERPASS_HEADERS)
                    if resp.status_code == 200:
                        return resp.json()
                    elif resp.status_code == 429:
                        # Rate-limited — back off and retry
                        wait = 2 ** (attempt + 1)  # 2s, 4s
                        print(f"[geospatial] Rate limited at {endpoint}, retrying in {wait}s...")
                        time.sleep(wait)
                        last_error = f"Rate limited at {endpoint}"
                        continue
                    else:
                        last_error = f"{endpoint} returned {resp.status_code}"
            except Exception as e:
                last_error = f"{endpoint}: {e}"
                continue
        # Brief pause between full rounds through endpoints
        if attempt < retries:
            time.sleep(1)
    raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_error}")


def _query_geomap_api(lat: float, lng: float, categories: str, radius_m: int, api_key: str) -> List[Dict]:
    """Query OpenGeoMap / Geoapify Places API when an API key is provided."""
    url = f"https://api.geoapify.com/v2/places?categories={categories}&filter=circle:{lng},{lat},{radius_m}&limit=10&apiKey={api_key}"
    try:
        with httpx.Client(timeout=8.0) as client:
            res = client.get(url)
            if res.status_code == 200:
                features = res.json().get("features", [])
                places = []
                for f in features:
                    props = f.get("properties", {})
                    plat, plng = props.get("lat", lat), props.get("lon", lng)
                    name = props.get("name") or props.get("formatted") or "Facility"
                    dist = props.get("distance", 0) / 1000.0
                    if not dist and plat and plng:
                        dist = _haversine_km(lat, lng, plat, plng)
                    places.append({"name": name, "lat": plat, "lng": plng, "distance_km": round(dist, 3)})
                places.sort(key=lambda p: p["distance_km"])
                return places
    except Exception as e:
        print(f"[geospatial] GeoMap API error: {e}")
    return []


@lru_cache(maxsize=4096)
def get_nearby_hospitals(lat: float, lng: float, radius_m: int = 5000) -> List[Dict]:
    """Query for hospitals and clinics within `radius_m` of (lat, lng).
    
    Uses OpenGeoMap API if key configured, otherwise queries global OpenStreetMap Overpass.
    """
    from app.core.config import settings
    api_key = settings.OPENGEOMAP_API_KEY or settings.GEOAPIFY_API_KEY
    if api_key:
        geo_res = _query_geomap_api(lat, lng, "healthcare.hospital,healthcare.clinic", radius_m, api_key)
        if geo_res:
            return geo_res

    lat_r, lng_r = _round_coord(lat), _round_coord(lng)
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="hospital"](around:{radius_m},{lat_r},{lng_r});
      way["amenity"="hospital"](around:{radius_m},{lat_r},{lng_r});
      node["amenity"="clinic"](around:{radius_m},{lat_r},{lng_r});
      way["amenity"="clinic"](around:{radius_m},{lat_r},{lng_r});
    );
    out center 10;
    """
    try:
        result = _run_overpass_query(query)
    except Exception as e:
        print(f"[geospatial] Hospital query failed: {e}")
        return []

    hospitals = []
    for el in result.get("elements", []):
        if el.get("type") == "node":
            elat, elng = el["lat"], el["lon"]
        elif el.get("type") == "way":
            c = el.get("center", {})
            elat, elng = c.get("lat"), c.get("lon")
        else:
            continue
        tags = el.get("tags", {})
        name = tags.get("name", tags.get("amenity", "Unnamed facility"))
        dist = _haversine_km(lat_r, lng_r, elat, elng)
        hospitals.append({"name": name, "lat": elat, "lng": elng, "distance_km": round(dist, 3)})

    hospitals.sort(key=lambda h: h["distance_km"])
    return hospitals


@lru_cache(maxsize=4096)
def get_nearby_schools(lat: float, lng: float, radius_m: int = 3000) -> List[Dict]:
    """Query for schools, colleges, and educational facilities within `radius_m` of (lat, lng)."""
    from app.core.config import settings
    api_key = settings.OPENGEOMAP_API_KEY or settings.GEOAPIFY_API_KEY
    if api_key:
        geo_res = _query_geomap_api(lat, lng, "education.school,education.college,education.university", radius_m, api_key)
        if geo_res:
            return geo_res

    lat_r, lng_r = _round_coord(lat), _round_coord(lng)
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="school"](around:{radius_m},{lat_r},{lng_r});
      way["amenity"="school"](around:{radius_m},{lat_r},{lng_r});
      node["amenity"="kindergarten"](around:{radius_m},{lat_r},{lng_r});
      way["amenity"="kindergarten"](around:{radius_m},{lat_r},{lng_r});
      node["amenity"="college"](around:{radius_m},{lat_r},{lng_r});
      way["amenity"="college"](around:{radius_m},{lat_r},{lng_r});
      node["amenity"="university"](around:{radius_m},{lat_r},{lng_r});
      way["amenity"="university"](around:{radius_m},{lat_r},{lng_r});
    );
    out center 10;
    """
    try:
        result = _run_overpass_query(query)
    except Exception as e:
        print(f"[geospatial] School query failed: {e}")
        return []

    schools = []
    for el in result.get("elements", []):
        if el.get("type") == "node":
            elat, elng = el["lat"], el["lon"]
        elif el.get("type") == "way":
            c = el.get("center", {})
            elat, elng = c.get("lat"), c.get("lon")
        else:
            continue
        tags = el.get("tags", {})
        name = tags.get("name", tags.get("amenity", "Unnamed school"))
        dist = _haversine_km(lat_r, lng_r, elat, elng)
        schools.append({"name": name, "lat": elat, "lng": elng, "distance_km": round(dist, 3)})

    schools.sort(key=lambda s: s["distance_km"])
    return schools


@lru_cache(maxsize=4096)
def get_nearest_road_class(lat: float, lng: float, radius_m: int = 200) -> Optional[str]:
    """Query Overpass for the nearest road and return its class.

    Maps OSM highway tags to our internal road class system:
        motorway, trunk       → highway
        primary, secondary    → major_road
        tertiary              → arterial
        residential            → residential
        unclassified, service → local
        other                  → local
    """
    lat_r, lng_r = _round_coord(lat), _round_coord(lng)
    query = f"""
    [out:json][timeout:15];
    way(around:{radius_m},{lat_r},{lng_r})["highway"];
    out tags 5;
    """
    try:
        result = _run_overpass_query(query, timeout=15.0)
    except Exception as e:
        print(f"[geospatial] Road query failed: {e}")
        return None

    # Find the highest-classification road in the results
    elements = result.get("elements", [])
    if not elements:
        return None

    # Priority order — pick the most "important" road nearby
    priority_map = [
        ({"motorway", "trunk"}, "highway"),
        ({"primary", "secondary"}, "major_road"),
        ({"tertiary", "tertiary_link"}, "arterial"),
        ({"primary_link", "secondary_link"}, "arterial"),
        ({"residential", "living_street"}, "residential"),
        ({"unclassified", "service", "road"}, "local"),
    ]

    found_classes = set()
    for el in elements:
        highway = el.get("tags", {}).get("highway")
        if not highway:
            continue
        for valid_tags, class_name in priority_map:
            if highway in valid_tags:
                found_classes.add(class_name)
                break

    # Return the highest-priority class found
    for _, class_name in priority_map:
        if class_name in found_classes:
            return class_name
    return "local"


def get_nearest_hospital_distance(lat: float, lng: float) -> Optional[float]:
    """Return distance in km to nearest hospital, or None if not found."""
    hospitals = get_nearby_hospitals(lat, lng)
    if not hospitals:
        return None
    return hospitals[0]["distance_km"]


def get_nearest_school_distance(lat: float, lng: float) -> Optional[float]:
    """Return distance in km to nearest school, or None if not found."""
    schools = get_nearby_schools(lat, lng)
    if not schools:
        return None
    return schools[0]["distance_km"]


def get_location_context(lat: float, lng: float) -> Dict:
    """Get a complete geospatial context for a report location.

    Returns:
        {
            "nearest_hospital_km": float | None,
            "nearest_hospital_name": str | None,
            "nearest_school_km": float | None,
            "nearest_school_name": str | None,
            "road_class": str | None,
            "hospital_count_5km": int,
            "school_count_3km": int,
        }
    """
    hospitals = get_nearby_hospitals(lat, lng)
    schools = get_nearby_schools(lat, lng)
    road_class = get_nearest_road_class(lat, lng)

    nearest_hospital = hospitals[0] if hospitals else None
    nearest_school = schools[0] if schools else None

    return {
        "nearest_hospital_km": nearest_hospital["distance_km"] if nearest_hospital else None,
        "nearest_hospital_name": nearest_hospital["name"] if nearest_hospital else None,
        "nearest_school_km": nearest_school["distance_km"] if nearest_school else None,
        "nearest_school_name": nearest_school["name"] if nearest_school else None,
        "road_class": road_class,
        "hospital_count_5km": len(hospitals),
        "school_count_3km": len(schools),
    }
