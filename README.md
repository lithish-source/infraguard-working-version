# InfraGuard 🛡️

**AI-Assisted Crowd-Sourced Community Infrastructure Damage Mapping with Severity Prioritization**

A production-ready web platform where citizens report damaged public infrastructure (roads, bridges, drainage, streetlights, water pipelines, traffic signals, public buildings), and an AI engine analyzes photos, estimates severity, and prioritizes incidents using 9-factor geospatial analytics — all displayed on an interactive map for authorities.

---

## ✨ Key Features

| Module | What it does |
|---|---|
| **Authentication** | JWT-based login with citizen & admin roles, bcrypt password hashing, RBAC |
| **Citizen Reporting** | Upload photos, capture GPS, pick category, describe damage, track status |
| **AI Severity Assessment** | OpenCV preprocessing + hand-crafted features + hybrid rule-based/ML classifier → damage type, severity (Low/Moderate/High/Critical), confidence |
| **Crowd Validation** | Citizens confirm reports, vote on severity, add photos; credibility score accrues |
| **Priority Engine** | 9-factor weighted scoring: severity, verifications, population, road class, hospital/school proximity, utility importance, time urgency, verification status |
| **Geospatial Map** | Leaflet with clustered markers, heatmap, severity colors, district/category/status filters, popup cards |
| **Admin Dashboard** | KPIs, monthly trends, district analytics, category/severity distribution, response time |
| **Report Management** | Verify, reject, override severity, assign teams, update status, resolve |
| **AI Analytics** | Vulnerability heatmaps, repeat-incident detection, citizen participation metrics, response efficiency |
| **Notifications** | Submission confirmations, verification updates, status changes, critical alerts |
| **Dark/Light Theme** | Persistent theme toggle with system-preference default |
| **Docker Deployment** | One-command `docker compose up` with PostGIS, FastAPI, React, nginx |

---

## 🧱 Tech Stack

**Frontend**
- React 18 + Vite 5
- Tailwind CSS 3
- React Router 6
- Leaflet + react-leaflet + leaflet.markercluster + leaflet.heat
- Chart.js + react-chartjs-2 (Bar, Line, Doughnut, Radar)
- Axios with auto-refresh interceptor

**Backend (Java)**
- Java 17 + Spring Boot 3.2
- Spring Data JPA + Hibernate (with PostGIS support)
- Spring Security + JWT (jjwt 0.12.5)
- bcrypt password hashing
- Maven build
- Lombok for boilerplate reduction

**AI Module (Java)**
- **LLM Vision API** — Llama 4 Scout via Groq (or any OpenAI-compatible provider: GPT-4o, Together AI, Ollama). Optional — falls back to rule-based classifier when no API key is set.
- **Overpass API (OpenStreetMap)** — real nearby hospitals, schools, road classes for accurate priority scoring
- **Rule-based severity classifier** — pure Java fallback (always available)
- Custom priority engine (9-factor transparent weighted scoring, pure Java)

**Database**
- PostgreSQL 15 + PostGIS 3.3
- 10 normalized tables with FK constraints, indexes, triggers, and a summary view

**Infrastructure**
- Docker Compose (db + backend + frontend)
- nginx reverse proxy for production
- uvicorn ASGI server

---

## 📁 Project Structure

```
infraguard/
├── frontend/                  # React + Vite frontend (unchanged from before)
│   ├── src/
│   │   ├── components/        # Layout, Sidebar, StatCard, DamageMap, Charts
│   │   ├── context/           # AuthContext, ThemeContext
│   │   ├── pages/             # 12 pages: Home, Login, Register, Dashboard, etc.
│   │   ├── services/          # Axios API client + resource services
│   │   └── utils/             # helpers (formatters, badges, etc.)
│   └── package.json
│
├── backend-java/              # ⭐ Java Spring Boot backend (NEW)
│   ├── src/main/java/com/infraguard/
│   │   ├── InfraGuardApplication.java   # Main entry point
│   │   ├── config/                      # SecurityConfig, AppProperties, DataSeeder
│   │   ├── controller/                  # AuthController, ReportController, AdminController
│   │   ├── entity/                      # 10 JPA entities (User, Report, District, etc.)
│   │   ├── dto/                         # Request/response DTOs
│   │   ├── repository/                  # Spring Data JPA repositories
│   │   ├── service/                    # Business logic (auth, report, priority, analytics)
│   │   ├── security/                   # JWT filter, token provider, user details
│   │   ├── ai/                         # PriorityEngine, LlmService (Java)
│   │   └── exception/                  # GlobalExceptionHandler
│   ├── src/main/resources/
│   │   └── application.yml             # Spring Boot config
│   ├── src/test/java/                  # JUnit tests
│   └── pom.xml                         # Maven build
│
├── backend/                   # Original Python backend (deprecated — kept for reference)
│
├── database/                  # SQL scripts (shared by both backends)
│   ├── init.sql
│   ├── schema.sql             # 10 tables + PostGIS + triggers
│   └── seed.sql
│
├── docker/                    # Docker config
│   ├── backend-java.Dockerfile # Maven build → OpenJDK 17 runtime
│   ├── frontend.Dockerfile
│   └── nginx.conf
│
├── docs/                      # Documentation
├── sample_data/               # Demo images + JSON
├── scripts/                   # Setup scripts
├── docker-compose.yml         # One-command full stack (Java backend + Postgres + React)
└── README.md
```

---

## 🚀 Quick Start

### Option A: Docker (recommended)

```bash
# 1. Clone the project
cd /home/z/my-project

# 2. (Optional) configure env
cp docker/.env.example .env

# 3. Boot the full stack
docker compose up --build

# 4. Open:
#    Frontend: http://localhost:5173
#    Backend docs: http://localhost:8000/api/v1/docs
```

**Default admin login:** `admin@infraguard.gov` / `Admin@12345`  
**Demo citizen login:** `aarav.sharma0@example.com` / `Citizen@12345`

### Option B: Local development

See **[docs/INSTALLATION.md](docs/INSTALLATION.md)** for full step-by-step instructions.

Brief version:

```bash
# 1. Start PostgreSQL with PostGIS
docker run -d --name infraguard-db -p 5432:5432 \
  -e POSTGRES_USER=infraguard -e POSTGRES_PASSWORD=infraguard \
  -e POSTGRES_DB=infraguard postgis/postgis:15-3.4

# 2. Initialize schema
psql -h localhost -U infraguard -d infraguard -f database/init.sql

# 3. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# 4. AI model + sample data (one-time)
cd ..
python scripts/setup_sample_data.py

# 5. Frontend
cd frontend
npm install
npm run dev
```

---

## 🔐 Default Credentials

After seeding, the following accounts are available:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@infraguard.gov` | `Admin@12345` |
| Citizen (demo) | `aarav.sharma0@example.com` | `Citizen@12345` |

> ⚠️ **Change these in production** via environment variables `DEFAULT_ADMIN_EMAIL` and `DEFAULT_ADMIN_PASSWORD`.

---

## 🧪 Tests

```bash
# Backend + AI tests (pytest)
python -m pytest tests/ -v

# Frontend tests (vitest)
cd frontend && npm test
```

Test results: **41 passing** (27 backend+AI, 14 frontend component tests; 3 integration tests skipped when backend not running).

---

## 📚 Documentation

| Document | Description |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, data flow, design decisions |
| [docs/API.md](docs/API.md) | Complete REST API reference with examples |
| [docs/DATABASE.md](docs/DATABASE.md) | Schema, indexes, relationships, geospatial design |
| [docs/AI_MODEL.md](docs/AI_MODEL.md) | AI pipeline, feature engineering, priority engine math |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment guide |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | Local development setup |
| [docs/USER_MANUAL.md](docs/USER_MANUAL.md) | End-user (citizen) guide |
| [docs/ADMIN_MANUAL.md](docs/ADMIN_MANUAL.md) | Administrator guide |

---

## 🎯 Severity & Priority Logic

### AI Severity Levels

| Level | Weight | Color | Trigger (rule-based score) |
|---|---|---|---|
| Low | 1.0 | 🟢 Green | Score < 2.5 |
| Moderate | 2.5 | 🟡 Amber | 2.5 ≤ Score < 5.0 |
| High | 4.0 | 🔴 Red | 5.0 ≤ Score < 7.5 |
| Critical | 5.0 | 🟣 Purple | Score ≥ 7.5 |

Score is computed from: edge density, dark pixel ratio, crack length, damage area ratio, texture variance.

### Priority Score (0-100)

Nine weighted components:

| Component | Weight |
|---|---|
| AI severity | 28% |
| Verification count | 12% |
| Population impact | 10% |
| Road importance | 10% |
| Hospital proximity | 10% |
| Utility importance | 8% |
| Time urgency | 8% |
| Verification status | 7% |
| School proximity | 7% |

Resulting urgency bands:

| Score | Urgency | Response Time |
|---|---|---|
| ≥ 80 | Immediate | Within 2 hours |
| 60-79 | High | Within 6 hours |
| 40-59 | Medium | Within 24 hours |
| 20-39 | Low | Within 72 hours |
| < 20 | Minimal | Within 7 days |

---

## 🗺️ Map Features

- **Marker clustering** (Leaflet.markercluster) — collapses dense areas into cluster icons
- **Color-coded severity pins** — green/amber/red/purple for Low/Moderate/High/Critical
- **Heatmap layer** (Leaflet.heat) — toggleable density visualization weighted by severity
- **Popup cards** with image, severity badge, status, verifications, priority score
- **Live filters** by district, category, severity, status
- **Search by district / category** via URL query params

---

## 📊 Admin Dashboard

- KPI cards: total / pending / verified / resolved / critical / citizens / verifications / avg response time
- Critical alert banner when critical incidents > 0
- Severity distribution doughnut
- Monthly trend line (reports vs resolved)
- Category distribution bar (total vs critical)
- District analytics bar (reports / critical / resolved per district)
- Top critical reports list
- Recompute priorities button (refreshes time-urgency component)

---

## 🔌 Optional Integrations

### LLM Vision API (Llama 4 / GPT-4o)

The image severity classifier has three branches, tried in priority order:

1. **LLM Vision** (if `LLM_API_KEY` is set) — best accuracy on real photos
2. **ML classifier** (scikit-learn RandomForest, always available)
3. **Rule-based heuristics** (always available, transparent)

**Setup (free, 30 req/min):**
1. Get a free Groq API key at https://console.groq.com
2. Add to `docker/.env` or your shell:
   ```bash
   LLM_API_KEY=gsk_your_key_here
   LLM_API_BASE_URL=https://api.groq.com/openai/v1
   LLM_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
   ```
3. Restart: `docker compose up --build`

**Alternative providers:**
| Provider | `LLM_API_BASE_URL` | `LLM_VISION_MODEL` | Cost |
|---|---|---|---|
| Groq (Llama 4) | `https://api.groq.com/openai/v1` | `meta-llama/llama-4-scout-17b-16e-instruct` | Free |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | ~$0.01/image |
| Together AI | `https://api.together.xyz/v1` | `meta-vllama/Llama-3.2-90B-Vision-Instruct-Turbo` | ~$0.005/image |
| Local Ollama | `http://localhost:11434/v1` | `llama3.2-vision` | Free |

Verify it's enabled: `curl http://localhost:8000/health | jq .llm`

### Overpass API (OpenStreetMap) — Enabled by default

The priority engine queries OpenStreetMap in real time for:
- Nearest hospital within 5 km (real distance, not district-based estimate)
- Nearest school/college within 3 km
- Nearest road class (highway / major_road / arterial / residential / local)

**No setup required** — works out of the box. Results are cached per ~110m grid cell to avoid rate limits.

If Overpass is down (rare), the system gracefully falls back to district-based estimates.

---

## 🔒 Security

- **JWT access + refresh tokens** (HS256)
- **bcrypt** password hashing with sha256 pre-hash for >72-byte passwords
- **Role-based access control** — admin routes protected by `get_current_admin` dependency
- **CORS allowlist** configurable via env
- **File upload validation** — MIME type + size limits
- **Pydantic v2 validation** on every input
- **Audit log** — all admin actions recorded in `admin_actions` table

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `python -m pytest tests/ && cd frontend && npm test`
4. Submit a pull request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- PostGIS team for the geospatial database extension
- OpenStreetMap contributors for the base map tiles
- Scikit-learn and OpenCV communities for the ML/CV tooling
- Tailwind CSS for the design system

---

**Built with ❤️ for safer communities.**
