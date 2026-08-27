# Database Documentation

## Overview

InfraGuard uses **PostgreSQL 15** with the **PostGIS 3.3** extension for geospatial support. The schema is fully normalized (3NF) with appropriate foreign keys, indexes, check constraints, and triggers.

## Extensions

```sql
CREATE EXTENSION postgis;          -- Geometry types + spatial indexes
CREATE EXTENSION "uuid-ossp";      -- UUID generation (available if needed)
CREATE EXTENSION pg_trgm;          -- Trigram fuzzy text search
```

## Custom Types (Enums)

```sql
CREATE TYPE user_role AS ENUM ('citizen', 'admin', 'official');
CREATE TYPE report_status AS ENUM ('Reported', 'Verified', 'Rejected', 'Assigned', 'In Progress', 'Resolved');
CREATE TYPE severity_level AS ENUM ('Low', 'Moderate', 'High', 'Critical');
```

## Schema Diagram

```
┌──────────────┐       ┌─────────────────────┐
│  districts   │←──────│       users         │
└──────┬───────┘       └─────────┬───────────┘
       │                         │
       │  ┌──────────────────────┘
       │  │
       │  ▼
┌──────┴───────────────────────────────────┐
│                 reports                   │
│  - user_id (FK → users)                   │
│  - district_id (FK → districts)           │
│  - infrastructure_type_id (FK → infra)    │
│  - geom: GEOGRAPHY(POINT, 4326)           │
└──┬─────────┬─────────┬─────────────┬──────┘
   │         │         │             │
   │         │         │             │
   ▼         ▼         ▼             ▼
┌──────┐ ┌────────┐ ┌────────────┐ ┌──────────────┐
│images│ │verif-  │ │priority_   │ │notifications │
│      │ │ications│ │scores      │ │              │
└──────┘ └────────┘ └────────────┘ └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │admin_actions │
                       │  (audit log) │
                       └──────────────┘
```

## Tables

### `users`
Citizen and admin accounts.

| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| full_name | VARCHAR(150) | NOT NULL |
| email | VARCHAR(255) | UNIQUE, NOT NULL, indexed |
| phone | VARCHAR(20) | |
| password_hash | VARCHAR(255) | NOT NULL (bcrypt) |
| role | user_role | NOT NULL, default 'citizen' |
| is_active | BOOLEAN | NOT NULL, default TRUE |
| last_login_at | TIMESTAMP | |
| district_id | BIGINT | FK → districts(id) ON DELETE SET NULL |
| created_at, updated_at | TIMESTAMP | NOT NULL, default NOW() |

**Indexes:** `idx_users_role`, `idx_users_email_trgm` (GIN)

### `districts`
Administrative boundaries with PostGIS geometry.

| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| name | VARCHAR(150) | UNIQUE, NOT NULL |
| code | VARCHAR(20) | UNIQUE, NOT NULL |
| state | VARCHAR(100) | |
| population | INTEGER | |
| area_sq_km | DOUBLE PRECISION | |
| geom | GEOGRAPHY(POLYGON, 4326) | GiST index |
| centroid | GEOGRAPHY(POINT, 4326) | |
| created_at, updated_at | TIMESTAMP | |

### `infrastructure_types`
Reference table for damage categories.

| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| name | VARCHAR(100) | UNIQUE, NOT NULL |
| code | VARCHAR(20) | UNIQUE, NOT NULL |
| description | TEXT | |
| default_priority_weight | DOUBLE PRECISION | NOT NULL, default 5.0 |
| icon | VARCHAR(50) | emoji or icon name |

**Seeded categories:** Road, Bridge, Drainage, Streetlight, Water Pipeline, Public Building, Traffic Signal, Footpath, Public Toilet, Park Equipment

### `reports`
The central table — one row per damage report.

| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| reference_code | VARCHAR(30) | UNIQUE, NOT NULL (e.g. `RPT-20260811-A1B2C3`) |
| user_id | BIGINT | FK → users(id) ON DELETE CASCADE |
| district_id | BIGINT | FK → districts(id) ON DELETE SET NULL |
| infrastructure_type_id | BIGINT | FK → infrastructure_types(id) ON DELETE RESTRICT |
| title | VARCHAR(255) | NOT NULL |
| description | TEXT | NOT NULL |
| address | VARCHAR(500) | |
| latitude | DOUBLE PRECISION | NOT NULL |
| longitude | DOUBLE PRECISION | NOT NULL |
| geom | GEOGRAPHY(POINT, 4326) | GiST index |
| ai_severity | severity_level | |
| ai_confidence | DOUBLE PRECISION | 0.0-1.0 |
| ai_damage_type | VARCHAR(100) | |
| ai_features | JSONB | Full feature vector for auditability |
| final_severity | severity_level | Admin override |
| status | report_status | NOT NULL, default 'Reported' |
| credibility_score | DOUBLE PRECISION | NOT NULL, default 0.0 |
| verification_count | INTEGER | NOT NULL, default 0 |
| upvote_count | INTEGER | NOT NULL, default 0 |
| downvote_count | INTEGER | NOT NULL, default 0 |
| assigned_team | VARCHAR(150) | |
| resolution_notes | TEXT | |
| resolved_at | TIMESTAMP | |
| created_at, updated_at | TIMESTAMP | |

**Indexes:**
- `idx_reports_status` (status)
- `idx_reports_severity` (ai_severity)
- `idx_reports_user` (user_id)
- `idx_reports_district` (district_id)
- `idx_reports_infra` (infrastructure_type_id)
- `idx_reports_created` (created_at DESC)
- `idx_reports_status_severity` (composite)
- `idx_reports_geom` (GiST on geom)
- `idx_reports_title_trgm` (GIN for fuzzy search)

### `images`
Photos attached to reports.

| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| report_id | BIGINT | FK → reports(id) ON DELETE CASCADE |
| user_id | BIGINT | FK → users(id) ON DELETE SET NULL |
| file_path | VARCHAR(500) | NOT NULL (server filesystem) |
| file_url | VARCHAR(500) | NOT NULL (public URL) |
| file_size_bytes | INTEGER | |
| mime_type | VARCHAR(50) | |
| width, height | INTEGER | |
| is_primary | BOOLEAN | NOT NULL, default FALSE |
| caption | VARCHAR(255) | |
| created_at, updated_at | TIMESTAMP | |

**Partial index:** `idx_images_primary` on `(report_id, is_primary) WHERE is_primary = TRUE`

### `verifications`
Crowd validation records. One per user per report (unique constraint).

| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| report_id | BIGINT | FK → reports(id) ON DELETE CASCADE |
| user_id | BIGINT | FK → users(id) ON DELETE SET NULL |
| severity_vote | severity_level | optional |
| comment | TEXT | |
| is_confirmed | BOOLEAN | NOT NULL, default TRUE |
| image_path | VARCHAR(500) | optional verification photo |
| created_at, updated_at | TIMESTAMP | |

**Unique constraint:** `uq_verifications_report_user` on `(report_id, user_id)` — prevents double-verification.

### `priority_scores`
History of priority score computations. A new row is appended each time the score is recomputed, preserving audit history.

| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| report_id | BIGINT | FK → reports(id) ON DELETE CASCADE |
| score | DOUBLE PRECISION | NOT NULL (0-100) |
| rank | INTEGER | assigned after sorting |
| severity_component | DOUBLE PRECISION | 0-1 |
| verification_component | DOUBLE PRECISION | 0-1 |
| population_component | DOUBLE PRECISION | 0-1 |
| road_importance_component | DOUBLE PRECISION | 0-1 |
| hospital_proximity_component | DOUBLE PRECISION | 0-1 |
| school_proximity_component | DOUBLE PRECISION | 0-1 |
| utility_importance_component | DOUBLE PRECISION | 0-1 |
| time_urgency_component | DOUBLE PRECISION | 0-1 |
| verification_status_component | DOUBLE PRECISION | 0-1 |
| recommended_response_time | VARCHAR(50) | e.g. "Within 2 hours" |
| resource_urgency | VARCHAR(30) | e.g. "Immediate" |
| created_at, updated_at | TIMESTAMP | |

**Indexes:** `idx_priority_report`, `idx_priority_score` (DESC), `idx_priority_rank`

### `notifications`
User-facing alerts.

| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK → users(id) ON DELETE CASCADE |
| report_id | BIGINT | FK → reports(id) ON DELETE CASCADE |
| title | VARCHAR(255) | NOT NULL |
| message | TEXT | NOT NULL |
| type | VARCHAR(50) | NOT NULL, default 'info' |
| is_read | BOOLEAN | NOT NULL, default FALSE |
| created_at, updated_at | TIMESTAMP | |

**Notification types:** `info`, `success`, `warning`, `error`, `critical`

### `admin_actions`
Audit log of all admin mutations on reports.

| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| admin_id | BIGINT | FK → users(id) ON DELETE SET NULL |
| report_id | BIGINT | FK → reports(id) ON DELETE CASCADE |
| action | VARCHAR(50) | NOT NULL (e.g. `status_change`, `severity_override`, `assign_team`) |
| previous_value | TEXT | |
| new_value | TEXT | |
| notes | TEXT | |
| created_at, updated_at | TIMESTAMP | |

## Triggers

```sql
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

Applied to all 9 tables (excluding `priority_scores` which has its own logic).

## Views

### `v_report_summary`
Convenience view joining reports with districts, infrastructure types, and latest priority score:

```sql
SELECT * FROM v_report_summary WHERE effective_severity = 'Critical';
```

## Geospatial Queries (examples)

### Find reports within 1km of a point
```sql
SELECT id, title, ai_severity
FROM reports
WHERE ST_DWithin(
  geom,
  ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326)::geography,
  1000  -- meters
)
ORDER BY created_at DESC;
```

### Count reports per district (using containment)
```sql
SELECT d.name, COUNT(r.id) AS report_count
FROM districts d
LEFT JOIN reports r ON ST_Contains(d.geom::geometry, r.geom::geometry)
GROUP BY d.name;
```

### Heatmap aggregation (grid-based)
```sql
SELECT
  ST_SnapToGrid(geom, 0.005) AS cell,
  COUNT(*) AS weight
FROM reports
WHERE status != 'Rejected'
GROUP BY cell;
```

## Backup & Restore

```bash
# Backup
pg_dump -U infraguard -Fc infraguard > backup_$(date +%Y%m%d).dump

# Restore
pg_restore -U infraguard -d infraguard -c backup_20260811.dump
```

## Performance Notes

- GiST indexes on `geom` columns make spatial queries (`ST_DWithin`, `ST_Contains`) fast
- `pg_trgm` GIN indexes enable fuzzy text search with `ILIKE '%term%'` performance
- Composite index `(status, ai_severity)` optimizes the most common admin dashboard query
- Partial index on `images WHERE is_primary = TRUE` keeps the primary-image lookup fast
- `BIGSERIAL` (bigint) chosen over `SERIAL` (int) to future-proof against ID exhaustion
