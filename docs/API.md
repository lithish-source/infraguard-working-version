# API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs available at `/api/v1/docs` (Swagger UI) and `/api/v1/redoc` (ReDoc).

## Authentication

All endpoints except `auth/register`, `auth/login`, `auth/refresh`, and `health` require a JWT bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Admin endpoints additionally require `role == 'admin'`.

---

## Auth Endpoints

### POST /auth/register
Register a new citizen account.

**Request body:**
```json
{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+919999999999",
  "password": "StrongP@ss1",
  "role": "citizen"
}
```

**Response 201:**
```json
{
  "id": 12,
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+919999999999",
  "role": "citizen",
  "is_active": true,
  "created_at": "2026-08-11T10:00:00"
}
```

**Validation:**
- `email` must be a valid email format
- `password` must be ≥8 chars, contain at least one uppercase letter and one digit
- `role` must be `citizen` or `official` (admins are seeded, not self-registered)

### POST /auth/login
Authenticate and receive JWT tokens.

**Request body:**
```json
{
  "email": "jane@example.com",
  "password": "StrongP@ss1"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 12,
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "role": "citizen",
    "is_active": true
  }
}
```

### POST /auth/refresh
Exchange refresh token for new access token.

**Request body:**
```json
{ "refresh_token": "eyJ..." }
```

**Response 200:** Same shape as login response.

### POST /auth/logout
Stateless logout (client discards tokens).

---

## Report Endpoints

### POST /reports
Create a new infrastructure damage report with images.

**Content-Type:** `multipart/form-data`

**Form fields:**
| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | yes | Min 5 chars, max 255 |
| `description` | string | yes | Min 10 chars, max 5000 |
| `category_id` | int | yes | Infrastructure type ID |
| `latitude` | float | yes | -90 to 90 |
| `longitude` | float | yes | -180 to 180 |
| `address` | string | no | Max 500 chars |
| `district_id` | int | no | Auto-detected if omitted |
| `images` | file[] | yes | 1-5 images, ≤10MB each, jpg/png/webp |

**Response 201:** Full `ReportOut` including AI analysis and initial priority score.

```json
{
  "id": 42,
  "reference_code": "RPT-20260811-A1B2C3",
  "title": "Large pothole on MG Road",
  "description": "...",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "category_id": 1,
  "category_name": "Road",
  "ai_severity": "High",
  "ai_confidence": 0.87,
  "ai_damage_type": "Pothole",
  "final_severity": null,
  "status": "Reported",
  "credibility_score": 1.0,
  "verification_count": 0,
  "images": [
    {
      "id": 1,
      "file_url": "/uploads/rpt42_xxx.jpg",
      "is_primary": true
    }
  ],
  "priority": {
    "score": 62.5,
    "rank": null,
    "severity_component": 0.8,
    "verification_component": 0.0,
    "resource_urgency": "High",
    "recommended_response_time": "Within 6 hours"
  }
}
```

### GET /reports
List reports with filters and pagination.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number (≥1) |
| `page_size` | int | 20 | Items per page (1-100) |
| `status` | string | — | `Reported`, `Verified`, `Assigned`, `In Progress`, `Resolved`, `Rejected` |
| `severity` | string | — | `Low`, `Moderate`, `High`, `Critical` |
| `category_id` | int | — | Infrastructure type ID |
| `district_id` | int | — | District ID |
| `search` | string | — | Searches title, description, reference_code |
| `order_by` | string | `created_at_desc` | `created_at_desc`, `created_at_asc`, `priority_desc`, `severity_desc` |

**Response 200:**
```json
{
  "items": [ReportListItem, ...],
  "total": 142,
  "page": 1,
  "page_size": 20
}
```

### GET /reports/{id}
Fetch a single report with full details (images, verifications, priority).

### GET /reports/map
Get all reports as GeoJSON FeatureCollection (for the interactive map).

**Query params:** `district_id`, `category_id`, `severity`, `status`

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [73.8567, 18.5204] },
      "properties": {
        "id": 42,
        "reference_code": "RPT-...",
        "title": "...",
        "severity": "High",
        "severity_color": "#ef4444",
        "status": "Verified",
        "category": "Road",
        "verification_count": 5,
        "priority_score": 72.3,
        "image_url": "/uploads/..."
      }
    }
  ]
}
```

### GET /reports/heatmap
Get heatmap points as `[[lat, lng, weight], ...]` for Leaflet.heat.

**Query params:** `severity` (optional filter)

**Response:**
```json
{
  "points": [[18.52, 73.85, 0.8], [18.53, 73.86, 0.4], ...]
}
```

### GET /reports/me/my-reports
Get all reports submitted by the current user.

### POST /reports/{id}/verifications
Add a crowd verification to a report.

**Content-Type:** `multipart/form-data`

**Form fields:**
| Field | Type | Required | Description |
|---|---|---|---|
| `severity_vote` | string | no | `Low`/`Moderate`/`High`/`Critical` |
| `comment` | string | no | Max 1000 chars |
| `is_confirmed` | bool | yes | `true` = confirm, `false` = flag |
| `image` | file | no | Optional verification photo |

**Response 200:** Updated `ReportOut` with new verification included.

**Errors:**
- `400` — Verifying own report
- `409` — Already verified this report

---

## Reference Data

### GET /reference/infrastructure-types
List all infrastructure categories.

```json
[
  { "id": 1, "name": "Road", "code": "ROAD", "description": "...", "default_priority_weight": 7.0, "icon": "🛣️" },
  ...
]
```

### GET /reference/districts
List all districts.

---

## Admin Endpoints (require admin role)

### GET /admin/dashboard/summary
```json
{
  "total_reports": 142,
  "pending_reports": 23,
  "verified_reports": 45,
  "resolved_reports": 67,
  "critical_incidents": 8,
  "total_users": 256,
  "total_verifications": 389,
  "avg_response_time_hours": 18.5,
  "response_rate": 47.2
}
```

### GET /admin/analytics/severity
Severity distribution:
```json
[
  { "severity": "Low", "count": 45, "percentage": 31.7 },
  { "severity": "Moderate", "count": 38, "percentage": 26.8 },
  { "severity": "High", "count": 35, "percentage": 24.6 },
  { "severity": "Critical", "count": 24, "percentage": 16.9 }
]
```

### GET /admin/analytics/category
Category distribution with critical counts.

### GET /admin/analytics/monthly?months=6
Monthly trend (reports vs resolved).

### GET /admin/analytics/districts
Per-district breakdown.

### GET /admin/analytics/response-time
```json
{
  "avg_hours": 18.5,
  "min_hours": 1.2,
  "max_hours": 96.0
}
```

### GET /admin/analytics/repeat-incidents
Clusters of reports within 500m of each other for the same infra type.

### GET /admin/analytics/participation
```json
{
  "total_citizens": 256,
  "citizens_who_reported": 142,
  "citizens_who_verified": 89,
  "avg_verifications_per_report": 2.74
}
```

### POST /admin/reports/{id}/status
Update report status.

**Request body:**
```json
{
  "status": "Assigned",
  "notes": "Team dispatched",
  "assigned_team": "Team Alpha"
}
```

### POST /admin/reports/{id}/severity
Override AI severity.

**Request body:**
```json
{ "severity": "Critical", "notes": "Inspector confirmed" }
```

### POST /admin/reports/{id}/assign
Quick-assign a response team.

**Request body:**
```json
{ "team": "Team Bravo", "notes": "Closest available" }
```

### POST /admin/priority/recompute
Recompute priority scores for all open reports (refreshes time-urgency component).

---

## Notification Endpoints

### GET /notifications?unread_only=false
List current user's notifications (max 50, newest first).

### POST /notifications/{id}/read
Mark a single notification as read.

### POST /notifications/read-all
Mark all notifications as read.

---

## Error Responses

All errors return JSON:

```json
{
  "detail": "Human-readable error message",
  "code": "optional_error_code"
}
```

Common status codes:
- `400` — Validation error
- `401` — Not authenticated
- `403` — Not authorized (wrong role)
- `404` — Resource not found
- `409` — Conflict (duplicate)
- `413` — Upload too large
- `422` — Pydantic validation error (with field details)
- `500` — Internal server error

---

## Rate Limiting (production)

For production deployment, add rate limiting via `slowapi` or nginx:
- Auth endpoints: 5 req/min per IP
- Report creation: 10 req/hour per citizen
- Verifications: 20 req/hour per citizen
- Read endpoints: 100 req/min per token
