-- ============================================================
-- InfraGuard — Initial reference & seed data
-- Run AFTER schema.sql
-- ============================================================

-- Infrastructure types
INSERT INTO infrastructure_types (name, code, description, default_priority_weight, icon)
VALUES
    ('Road', 'ROAD', 'Surface roads including potholes, cracks, subsidence', 7.0, 'road'),
    ('Bridge', 'BRIDGE', 'Bridges, overpasses, flyovers', 9.5, 'bridge'),
    ('Drainage System', 'DRAINAGE', 'Storm drains, culverts, canals', 6.0, 'water'),
    ('Streetlight', 'STREETLIGHT', 'Public street lighting', 4.0, 'lightbulb'),
    ('Water Pipeline', 'WATER', 'Public water supply pipelines', 8.5, 'faucet'),
    ('Public Building', 'BUILDING', 'Government offices, schools, hospitals', 7.5, 'building'),
    ('Traffic Signal', 'TRAFFIC', 'Traffic lights and signaling', 8.0, 'traffic'),
    ('Footpath', 'FOOTPATH', 'Pedestrian walkways', 3.5, 'walking'),
    ('Public Toilet', 'TOILET', 'Sanitation facilities', 3.0, 'restroom'),
    ('Park Equipment', 'PARK', 'Benches, playground equipment', 2.5, 'tree')
ON CONFLICT (code) DO NOTHING;

-- Districts (centroids around Pune, India for demo)
INSERT INTO districts (name, code, state, population, area_sq_km, centroid)
VALUES
    ('Central District', 'CD', 'Maharashtra', 850000, 75.0,
     ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326)),
    ('North District', 'ND', 'Maharashtra', 620000, 92.0,
     ST_SetSRID(ST_MakePoint(73.8267, 18.5804), 4326)),
    ('South District', 'SD', 'Maharashtra', 730000, 88.0,
     ST_SetSRID(ST_MakePoint(73.8667, 18.4604), 4326)),
    ('East District', 'ED', 'Maharashtra', 540000, 110.0,
     ST_SetSRID(ST_MakePoint(73.9367, 18.5404), 4326)),
    ('West District', 'WD', 'Maharashtra', 690000, 84.0,
     ST_SetSRID(ST_MakePoint(73.7867, 18.5104), 4326))
ON CONFLICT (code) DO NOTHING;

-- Default administrator (password hash will be replaced by app on first run).
-- The hash below is for "Admin@12345" — bcrypt with cost 12.
-- Replace via the Python seed script: `python -m app.seed`
INSERT INTO users (full_name, email, password_hash, role, is_active)
VALUES (
    'System Administrator',
    'admin@infraguard.gov',
    '$2b$12$placeholder_replaced_by_python_seed',
    'admin',
    TRUE
)
ON CONFLICT (email) DO NOTHING;
