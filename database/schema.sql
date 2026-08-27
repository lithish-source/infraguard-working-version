-- ============================================================
-- InfraGuard — Complete SQL Schema
-- AI-Assisted Crowd-Sourced Community Infrastructure Damage Mapping
-- with Severity Prioritization
--
-- Database: PostgreSQL 15+ with PostGIS 3.3+ extension
--
-- NOTE: We use VARCHAR + CHECK constraints instead of native ENUM types
-- to keep the schema compatible with SQLAlchemy ORM string columns.
-- ============================================================

-- Required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- Table: districts
-- ============================================================
CREATE TABLE IF NOT EXISTS districts (
    id            BIGSERIAL PRIMARY KEY,
    name          VARCHAR(150) NOT NULL UNIQUE,
    code          VARCHAR(20)  NOT NULL UNIQUE,
    state         VARCHAR(100),
    population    INTEGER,
    area_sq_km    DOUBLE PRECISION,
    geom          GEOMETRY(POLYGON, 4326),
    centroid      GEOMETRY(POINT, 4326),
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_districts_code CHECK (code ~ '^[A-Z]{1,20}$')
);
CREATE INDEX IF NOT EXISTS idx_districts_name_trgm ON districts USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_districts_geom ON districts USING gist (geom);

-- ============================================================
-- Table: infrastructure_types
-- ============================================================
CREATE TABLE IF NOT EXISTS infrastructure_types (
    id                       BIGSERIAL PRIMARY KEY,
    name                     VARCHAR(100) NOT NULL UNIQUE,
    code                     VARCHAR(20)  NOT NULL UNIQUE,
    description              TEXT,
    default_priority_weight  DOUBLE PRECISION NOT NULL DEFAULT 5.0,
    icon                     VARCHAR(50),
    created_at               TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Table: users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    full_name       VARCHAR(150) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    phone           VARCHAR(20),
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'citizen',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMP,
    district_id     BIGINT REFERENCES districts(id) ON DELETE SET NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_users_role CHECK (role IN ('citizen', 'admin', 'official'))
);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_email_trgm ON users USING gin (email gin_trgm_ops);

-- ============================================================
-- Table: reports
-- ============================================================
CREATE TABLE IF NOT EXISTS reports (
    id                       BIGSERIAL PRIMARY KEY,
    reference_code           VARCHAR(30) NOT NULL UNIQUE,
    user_id                  BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    district_id              BIGINT REFERENCES districts(id) ON DELETE SET NULL,
    infrastructure_type_id   BIGINT NOT NULL REFERENCES infrastructure_types(id) ON DELETE RESTRICT,

    title                    VARCHAR(255) NOT NULL,
    description              TEXT NOT NULL,
    address                  VARCHAR(500),

    latitude                 DOUBLE PRECISION NOT NULL,
    longitude                DOUBLE PRECISION NOT NULL,
    geom                     GEOMETRY(POINT, 4326),

    ai_severity              VARCHAR(20),
    ai_confidence            DOUBLE PRECISION,
    ai_damage_type           VARCHAR(100),
    ai_features              JSONB,

    final_severity           VARCHAR(20),

    status                   VARCHAR(30) NOT NULL DEFAULT 'Reported',
    credibility_score        DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    verification_count       INTEGER NOT NULL DEFAULT 0,
    upvote_count             INTEGER NOT NULL DEFAULT 0,
    downvote_count           INTEGER NOT NULL DEFAULT 0,

    assigned_team            VARCHAR(150),
    resolution_notes         TEXT,
    resolved_at              TIMESTAMP,

    created_at               TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_reports_status CHECK (
        status IN ('Reported','Verified','Rejected','Assigned','In Progress','Resolved')
    ),
    CONSTRAINT ck_reports_ai_severity CHECK (
        ai_severity IS NULL OR ai_severity IN ('Low','Moderate','High','Critical')
    ),
    CONSTRAINT ck_reports_final_severity CHECK (
        final_severity IS NULL OR final_severity IN ('Low','Moderate','High','Critical')
    )
);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_severity ON reports(ai_severity);
CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_district ON reports(district_id);
CREATE INDEX IF NOT EXISTS idx_reports_infra ON reports(infrastructure_type_id);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_status_severity ON reports(status, ai_severity);
CREATE INDEX IF NOT EXISTS idx_reports_geom ON reports USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_reports_title_trgm ON reports USING gin (title gin_trgm_ops);

-- ============================================================
-- Table: images
-- ============================================================
CREATE TABLE IF NOT EXISTS images (
    id              BIGSERIAL PRIMARY KEY,
    report_id       BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    file_path       VARCHAR(500) NOT NULL,
    file_url        VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER,
    mime_type       VARCHAR(50),
    width           INTEGER,
    height          INTEGER,
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
    caption         VARCHAR(255),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_images_report ON images(report_id);
CREATE INDEX IF NOT EXISTS idx_images_primary ON images(report_id, is_primary) WHERE is_primary = TRUE;

-- ============================================================
-- Table: verifications (crowd validation)
-- ============================================================
CREATE TABLE IF NOT EXISTS verifications (
    id              BIGSERIAL PRIMARY KEY,
    report_id       BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    severity_vote   VARCHAR(20),
    comment         TEXT,
    is_confirmed    BOOLEAN NOT NULL DEFAULT TRUE,
    image_path      VARCHAR(500),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_verifications_report_user UNIQUE (report_id, user_id),
    CONSTRAINT ck_verifications_severity_vote CHECK (
        severity_vote IS NULL OR severity_vote IN ('Low','Moderate','High','Critical')
    )
);
CREATE INDEX IF NOT EXISTS idx_verifications_report ON verifications(report_id);
CREATE INDEX IF NOT EXISTS idx_verifications_user ON verifications(user_id);

-- ============================================================
-- Table: priority_scores
-- ============================================================
CREATE TABLE IF NOT EXISTS priority_scores (
    id                            BIGSERIAL PRIMARY KEY,
    report_id                     BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    score                         DOUBLE PRECISION NOT NULL,
    rank                          INTEGER,

    severity_component            DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    verification_component        DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    population_component          DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    road_importance_component     DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    hospital_proximity_component  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    school_proximity_component    DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    utility_importance_component  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    time_urgency_component        DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    verification_status_component DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    recommended_response_time     VARCHAR(50),
    resource_urgency              VARCHAR(30),
    created_at                    TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                    TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_priority_report ON priority_scores(report_id);
CREATE INDEX IF NOT EXISTS idx_priority_score ON priority_scores(score DESC);
CREATE INDEX IF NOT EXISTS idx_priority_rank ON priority_scores(rank);

-- ============================================================
-- Table: notifications
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_id   BIGINT REFERENCES reports(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    message     TEXT NOT NULL,
    type        VARCHAR(50) NOT NULL DEFAULT 'info',
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);

-- ============================================================
-- Table: admin_actions (audit log)
-- ============================================================
CREATE TABLE IF NOT EXISTS admin_actions (
    id              BIGSERIAL PRIMARY KEY,
    admin_id        BIGINT REFERENCES users(id) ON DELETE SET NULL,
    report_id       BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    action          VARCHAR(50) NOT NULL,
    previous_value  TEXT,
    new_value       TEXT,
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_actions_admin ON admin_actions(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_report ON admin_actions(report_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_created ON admin_actions(created_at DESC);

-- ============================================================
-- updated_at triggers
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ DECLARE t TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'districts','infrastructure_types','users','reports','images',
        'verifications','priority_scores','notifications','admin_actions'
    ])
    LOOP
        EXECUTE format($f$
            DROP TRIGGER IF EXISTS trg_%s_updated ON %s;
            CREATE TRIGGER trg_%s_updated BEFORE UPDATE ON %s
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        $f$, t, t, t, t);
    END LOOP;
END $$;

-- ============================================================
-- Helpful view
-- ============================================================
CREATE OR REPLACE VIEW v_report_summary AS
SELECT
    r.id, r.reference_code, r.title, r.status,
    r.ai_severity, r.final_severity,
    COALESCE(r.final_severity, r.ai_severity) AS effective_severity,
    r.verification_count, r.credibility_score,
    d.name AS district_name,
    it.name AS category_name,
    (SELECT MAX(score) FROM priority_scores WHERE report_id = r.id) AS latest_priority_score,
    r.created_at, r.resolved_at
FROM reports r
LEFT JOIN districts d ON d.id = r.district_id
LEFT JOIN infrastructure_types it ON it.id = r.infrastructure_type_id;
