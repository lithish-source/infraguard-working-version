# System Architecture

## Overview

InfraGuard is a three-tier web application with an AI inference layer embedded in the backend. It follows a clean modular architecture where each concern is isolated: data models, schemas, services, API routes, AI pipeline, and frontend state.

```
┌─────────────────────────────────────────────────────────────┐
│                     BROWSER (User)                          │
│  React SPA · Tailwind · Leaflet · Chart.js · Axios         │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS / JWT
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  nginx (Reverse Proxy)                      │
│  - Serves static React build                                │
│  - Proxies /api/* and /uploads/* to backend                 │
│  - gzip, cache headers                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                FastAPI Backend (uvicorn)                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ API Layer (app/api/v1)                              │    │
│  │  auth · reports · reference · admin · notifications│    │
│  └──────────────────┬─────────────────────────────────┘    │
│                     │ Depends(get_db), Depends(get_current_user) │
│  ┌──────────────────▼─────────────────────────────────┐    │
│  │ Service Layer (app/services)                        │    │
│  │  auth_service · report_service · priority_service   │    │
│  │  analytics_service · map_service                    │    │
│  └──────────────────┬─────────────────────────────────┘    │
│                     │                                         │
│  ┌──────────────────▼─────────────────────────────────┐    │
│  │ AI Module (ai/)                                     │    │
│  │  SeverityAnalyzer · PriorityEngine · Preprocessor   │    │
│  │  Feature extraction · Rule-based + ML classifier    │    │
│  └──────────────────┬─────────────────────────────────┘    │
│                     │                                         │
│  ┌──────────────────▼─────────────────────────────────┐    │
│  │ Data Layer (SQLAlchemy ORM + GeoAlchemy2)           │    │
│  │  10 models: User, District, InfraType, Report, ...  │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │ asyncpg / psycopg2
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            PostgreSQL 15 + PostGIS 3.3                      │
│  - Geometry columns (POINT, POLYGON) with SRID 4326         │
│  - GiST indexes for geospatial queries                       │
│  - pg_trgm for fuzzy text search                            │
│  - Audit triggers (set_updated_at)                          │
└─────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. Presentation Layer (React SPA)
- **Routing** — React Router 6 with protected routes (citizen vs admin)
- **State** — React Context for Auth + Theme; component-level state elsewhere
- **API access** — Axios with JWT interceptor + 401 auto-refresh
- **Visualization** — Leaflet for maps, Chart.js for analytics
- **Theme** — Tailwind dark mode (`class` strategy) with localStorage persistence

### 2. API Layer (FastAPI routers)
- Thin controllers — only validate input, call services, format responses
- Use Pydantic v2 schemas for request/response models
- Dependency injection for DB session and current user
- OpenAPI docs auto-generated at `/api/v1/docs`

### 3. Service Layer
- All business logic lives here
- `auth_service` — registration, login, token issuance
- `report_service` — CRUD, verifications, status transitions, admin actions
- `priority_service` — wraps AI `PriorityEngine`, persists `PriorityScore` rows
- `analytics_service` — dashboard KPIs, distributions, repeat-incident detection
- `map_service` — GeoJSON FeatureCollection builders + heatmap points

### 4. AI Module
Standalone Python package imported by the backend (not coupled to FastAPI):
- **Preprocessor** — load image (file/bytes/PIL/numpy), resize with padding, denoise (bilateral filter), CLAHE contrast enhancement, edge detection
- **Feature Extractor** — 13 numeric features (edge density, dark pixel ratio, crack length proxy, damage area ratio, texture variance, mean RGB, std RGB, mean saturation/value)
- **SeverityAnalyzer** — hybrid: always-available rule-based classifier + optional ML (RandomForest). Confidence = average of rule confidence and ML probability
- **PriorityEngine** — 9 weighted components normalized to [0,1] → score [0,100], with explainable per-component breakdown

### 5. Data Layer
- SQLAlchemy 2.0 ORM with `declarative_base`
- GeoAlchemy2 `Geometry` columns for PostGIS integration
- 10 tables, fully normalized with FKs, indexes, and check constraints
- `updated_at` triggers via `set_updated_at()` PL/pgSQL function
- Audit log in `admin_actions` table for all admin mutations

## Data Flow: Report Submission

```
1. Citizen fills form + uploads photos
2. POST /api/v1/reports (multipart/form-data)
3. Backend saves images to /uploads
4. For primary image:
   a. SeverityAnalyzer.analyze_image(file_path)
   b. Preprocess → extract features → rule-based + ML classifier
   c. Returns {severity, confidence, damage_type, features}
5. Report row created with ai_severity, ai_confidence, ai_damage_type
6. PriorityEngine.compute(severity, verifications, district, ...)
   → PriorityScore row created
7. Notification row created for the user
8. Response: full ReportOut with images + priority + AI analysis
```

## Data Flow: Crowd Verification

```
1. Other citizen opens report detail page
2. Clicks "Confirm" with optional severity vote + photo
3. POST /api/v1/reports/{id}/verifications (multipart)
4. Backend:
   a. Check user hasn't already verified (unique constraint)
   b. Create Verification row
   c. Increment report.verification_count, upvote_count
   d. Add 1.0 to credibility_score (capped at 10)
   e. If verification_count >= 3 and status == "Reported":
      → auto-promote to "Verified"
   f. Recompute priority (verification_component rises)
   g. Notify original reporter
```

## Data Flow: Priority Recomputation

```
Trigger events:
  - New report created
  - New verification added
  - Admin changes severity
  - Admin clicks "Recompute Priorities" button

Process:
  1. Load report + district + infrastructure_type
  2. Compute 9 normalized components (each in [0,1])
  3. Apply weights:
       severity: 28%, verification: 12%, population: 10%, road: 10%,
       hospital: 10%, school: 7%, utility: 8%, time: 8%, status: 7%
  4. Multiply sum by credibility factor (0.9-1.1)
  5. Scale to 0-100
  6. Determine urgency band + recommended response time
  7. Persist new PriorityScore row (history preserved)
```

## Authentication & Authorization

- **JWT** tokens (HS256), 24h access, 7d refresh
- **RBAC**: `citizen`, `admin`, `official` roles
- Backend dependency: `get_current_user` (validates JWT, loads User)
- Backend dependency: `get_current_admin` (extends above, checks `role == 'admin'`)
- Frontend: `ProtectedRoute` component wraps routes requiring auth
- Frontend: `ProtectedRoute requireAdmin` for admin-only routes

## Geospatial Design

- All reports have `latitude`/`longitude` (float) + `geom` (PostGIS Point, SRID 4326)
- Districts have `geom` (Polygon) + `centroid` (Point)
- GiST indexes on geometry columns for fast spatial queries
- Map endpoint returns GeoJSON FeatureCollection
- Heatmap endpoint returns `[[lat, lng, weight], ...]` for Leaflet.heat

## Extensibility

| Want to... | Where to extend |
|---|---|
| Add new infrastructure category | Insert into `infrastructure_types` table |
| Add new severity level | Update `SEVERITY_LEVELS` in `ai/severity_classifier.py` + DB check constraint |
| Tune priority weights | Edit `WEIGHTS` dict in `ai/priority_engine.py` |
| Swap ML model | Replace `ai/models/severity_classifier.joblib` (keep `{model, scaler, feature_names, labels}` shape) |
| Add new admin action | Add endpoint in `app/api/v1/admin.py` + service method |
| Add new chart | Add chart component in `frontend/src/components/Charts.jsx` |
| Add new notification type | Insert row in `notifications` table with `type` field |

## Performance Considerations

- Marker clustering client-side (Leaflet.markercluster) handles 10k+ markers
- Backend list endpoints paginated (default 20, max 100)
- Indexes on `reports(status)`, `reports(ai_severity)`, `reports(created_at)`, `priority_scores(score DESC)`
- AI inference ~50-150ms per image (single-threaded)
- Database connection pool: 10 base + 20 overflow (configurable)

## Security Posture

- All passwords hashed with bcrypt (12 rounds) + sha256 pre-hash for >72-byte safety
- JWT secret loaded from env, never committed
- File uploads: MIME-type allowlist (jpeg/png/webp), size limit (10MB default)
- CORS allowlist (not `*`)
- Pydantic v2 input validation on every endpoint
- SQL injection impossible (SQLAlchemy ORM throughout)
- XSS: React escapes by default; no `dangerouslySetInnerHTML`
- CSRF: JWT in `Authorization` header (not cookies) → CSRF not applicable
