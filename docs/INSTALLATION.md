# Installation Guide (Local Development)

This guide walks you through setting up InfraGuard on your local machine for development.

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Backend + AI module |
| Node.js | 20+ | Frontend build |
| PostgreSQL | 15+ | Database |
| PostGIS | 3.3+ | Geospatial extension |
| Git | any | Clone the repo |

### OS-specific setup

#### Ubuntu / Debian
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
  nodejs npm postgresql postgresql-15-postgis-3 nginx \
  build-essential libpq-dev gdal-bin
```

#### macOS (Homebrew)
```bash
brew install python@3.11 node postgis gdal
brew services start postgresql
```

#### Windows (WSL2 recommended)
Use WSL2 with Ubuntu and follow the Ubuntu instructions.

---

## Step 1: Start PostgreSQL with PostGIS

### Option A: Docker (easiest)

```bash
docker run -d --name infraguard-db \
  -p 5432:5432 \
  -e POSTGRES_USER=infraguard \
  -e POSTGRES_PASSWORD=infraguard \
  -e POSTGRES_DB=infraguard \
  postgis/postgis:15-3.4
```

### Option B: Native install

```bash
# Start PostgreSQL service
sudo systemctl start postgresql

# Create user and database
sudo -u postgres createuser infraguard -P  # Enter "infraguard" when prompted
sudo -u postgres createdb infraguard -O infraguard

# Enable PostGIS extension
sudo -u postgres psql -d infraguard -c "CREATE EXTENSION postgis; CREATE EXTENSION pg_trgm;"
```

---

## Step 2: Initialize Database Schema

```bash
cd /home/z/my-project

# Apply schema
psql -h localhost -U infraguard -d infraguard -f database/schema.sql

# Apply seed (reference data)
psql -h localhost -U infraguard -d infraguard -f database/seed.sql
```

You should see: `CREATE TABLE`, `CREATE INDEX`, `INSERT 0 1` etc.

---

## Step 3: Backend Setup

```bash
cd /home/z/my-project/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env if your DB credentials differ:
#   DATABASE_URL=postgresql+psycopg2://infraguard:infraguard@localhost:5432/infraguard

# Seed the database (creates admin user, demo citizens, demo reports)
python -m app.seed

# Start the dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend's lifespan hook will:
1. Create all tables (idempotent)
2. Seed reference data + admin user + demo reports
3. Train the AI model on first run if missing

**Verify backend is running:**
```bash
curl http://localhost:8000/health
# {"status":"healthy","ai_ready":true}
```

**Open API docs:** http://localhost:8000/api/v1/docs

---

## Step 4: AI Model Setup (one-time)

The backend auto-trains the AI model on first start. To manually train it:

```bash
cd /home/z/my-project
python scripts/setup_sample_data.py
```

This will:
1. Generate 24 sample damage images in `sample_data/images/`
2. Train a RandomForest classifier (300 samples × 4 severity levels)
3. Save the model to `ai/models/severity_classifier.joblib`

Expected output:
```
[generate_sample_data] Wrote 24 sample images to /home/z/my-project/sample_data/images
[train] Accuracy: 0.9958
[train] Saved model to /home/z/my-project/ai/models/severity_classifier.joblib
[setup] Done.
```

---

## Step 5: Frontend Setup

```bash
cd /home/z/my-project/frontend

# Install dependencies
npm install

# Start the dev server (hot reload)
npm run dev
```

**Open the app:** http://localhost:5173

The Vite dev server proxies `/api/*` and `/uploads/*` to the backend on port 8000, so you don't need to configure CORS for local development.

---

## Step 6: Verify the Stack

1. **Frontend loads:** http://localhost:5173 — you should see the InfraGuard landing page
2. **Login as admin:** Click "Sign In" → use the "👮 Admin" quick-fill button → "Sign In"
3. **Admin dashboard:** You should see KPIs, charts, and demo reports
4. **View map:** Click "Damage Map" in the sidebar — markers should appear around Pune, India
5. **Submit a report:** Click "Submit Report" → fill the form → upload a sample image from `sample_data/images/` → submit
6. **AI analysis:** The report details page should show AI severity, confidence, and priority score

---

## Default Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@infraguard.gov` | `Admin@12345` |
| Demo Citizen | `aarav.sharma0@example.com` | `Citizen@12345` |

---

## Running Tests

### Backend + AI Tests

```bash
cd /home/z/my-project
python -m pytest tests/ -v
```

Expected: `27 passed, 3 skipped` (skipped tests require running backend).

### Frontend Tests

```bash
cd /home/z/my-project/frontend
npm test
```

### Integration Tests (requires running backend)

```bash
# Start the backend first, then:
cd /home/z/my-project
python -m pytest tests/test_integration.py -v
```

---

## Troubleshooting

### "Could not connect to database"
- Verify PostgreSQL is running: `pg_isready -h localhost -p 5432`
- Check credentials in `backend/.env`
- For Docker DB: `docker ps` to confirm the container is up

### "AI model not loaded"
- Check that `ai/models/severity_classifier.joblib` exists
- Re-run `python scripts/setup_sample_data.py`
- Check backend logs: `uvicorn` should print `[main] Default AI model trained.` on first start

### "Map markers don't appear"
- Open browser dev tools → Network tab → check `/api/v1/reports/map` returns 200
- Verify reports exist: `psql -U infraguard -d infraguard -c "SELECT COUNT(*) FROM reports;"`
- If empty, re-seed: `cd backend && python -m app.seed`

### "CORS error in browser console"
- The Vite dev server should proxy API requests — verify `vite.config.js` has the proxy config
- If running frontend separately, add your origin to `BACKEND_CORS_ORIGINS` in `backend/.env`

### "Upload fails with 413"
- Increase `MAX_UPLOAD_SIZE_MB` in `backend/.env`
- For nginx deployments, also set `client_max_body_size` in nginx config

### "bcrypt error"
- If you see `password cannot be longer than 72 bytes`, ensure you're using the latest backend code (we sha256 pre-hash long passwords)

---

## Development Workflow

### Backend hot reload
```bash
cd backend
uvicorn app.main:app --reload  # auto-restarts on file changes
```

### Frontend hot reload
```bash
cd frontend
npm run dev  # Vite HMR
```

### Database reset (DESTRUCTIVE)
```bash
# Drop and recreate all tables
psql -U infraguard -d infraguard -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -U infraguard -d infraguard -f database/schema.sql
psql -U infraguard -d infraguard -f database/seed.sql
cd backend && python -m app.seed  # Re-seed admin + demo data
```

### Re-train AI model
```bash
cd /home/z/my-project
python -m ai.train  # Or: python scripts/setup_sample_data.py
```

---

## IDE Setup

### VSCode recommended extensions
- Python (Microsoft)
- Pylance
- ESLint
- Tailwind CSS IntelliSense
- PostgreSQL (Chris Kolkman)
- GitLens

### Recommended settings.json
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "tailwindCSS.experimental.classRegex": [
    "className=\"([^\"]*)\""
  ]
}
```
