# Deployment Guide

This guide covers production deployment of InfraGuard using Docker Compose, with notes on bare-metal and cloud deployments.

## Option A: Docker Compose (Recommended)

### Prerequisites
- Docker 24+
- Docker Compose v2+
- 2GB+ RAM available
- 20GB+ disk space

### Steps

```bash
# 1. Clone or copy the project
cd /path/to/infraguard

# 2. Create production .env (NEVER commit this)
cp docker/.env.example .env
nano .env  # Edit JWT_SECRET_KEY and admin credentials

# 3. Build and start the stack
docker compose up --build -d

# 4. Verify all services are healthy
docker compose ps
docker compose logs -f --tail=50 backend

# 5. Initialize AI model (first run only — the backend does this automatically,
#    but you can force it):
docker compose exec backend python /app/../scripts/setup_sample_data.py
# Note: in container, the script path is /app/scripts/setup_sample_data.py
# (adjust if needed — alternatively, the backend's lifespan hook trains the
# model automatically on first run if missing)

# 6. Access:
#    Frontend: http://localhost:5173
#    Backend API docs: http://localhost:8000/api/v1/docs
```

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `JWT_SECRET_KEY` | **YES** | — | 32+ char random string for JWT signing |
| `DEFAULT_ADMIN_EMAIL` | no | `admin@infraguard.gov` | Initial admin email |
| `DEFAULT_ADMIN_PASSWORD` | no | `Admin@12345` | Initial admin password (CHANGE IN PRODUCTION) |

Other env vars (with defaults) are in `backend/.env.example`.

### Stopping

```bash
docker compose down           # Stop containers, keep volumes
docker compose down -v        # Stop + delete database + uploads (DESTRUCTIVE)
```

### Viewing Logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

### Backup

```bash
# Backup database
docker compose exec db pg_dump -U infraguard infraguard | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup uploaded images
docker compose cp backend:/app/backend/uploads ./uploads_backup

# Restore database
gunzip -c backup_20260811.sql.gz | docker compose exec -T db psql -U infraguard infraguard
```

---

## Option B: Cloud Deployment (AWS Example)

### Architecture

```
                    ┌─────────────────┐
                    │   Route 53      │  DNS: infraguard.gov
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  CloudFront     │  CDN + HTTPS
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │  S3       │  │  ALB      │  │  ALB      │
        │ (frontend)│  │ (API)     │  │ (uploads) │
        └───────────┘  └─────┬─────┘  └─────┬─────┘
                             │              │
                      ┌──────▼──────┐ ┌─────▼─────┐
                      │  ECS Fargate│ │  EC2 /    │
                      │  (FastAPI)  │ │  EFS      │
                      └──────┬──────┘ │  (images) │
                             │        └───────────┘
                      ┌──────▼──────┐
                      │  RDS        │
                      │  PostgreSQL │
                      │  + PostGIS  │
                      └─────────────┘
```

### Steps

1. **Database**: Provision RDS for PostgreSQL 15 with PostGIS extension
   ```sql
   CREATE EXTENSION postgis;
   CREATE EXTENSION pg_trgm;
   ```
   Apply `database/schema.sql` and `database/seed.sql`.

2. **Object storage**: Create an S3 bucket for uploaded images. Update backend's `UPLOAD_DIR` to use S3 (requires code change in `report_service._save_upload` to use boto3).

3. **Backend**: Build the Docker image from `docker/backend.Dockerfile`, push to ECR, deploy to ECS Fargate. Set env vars:
   - `DATABASE_URL=postgresql+psycopg2://...rds.amazonaws.com/infraguard`
   - `JWT_SECRET_KEY=<strong-secret>`
   - `UPLOAD_DIR=/mnt/efs/uploads` (or S3 path)
   - `BACKEND_CORS_ORIGINS=["https://infraguard.gov"]`

4. **Frontend**: Build static assets (`npm run build`), upload `dist/` to S3, configure CloudFront distribution with SPA fallback.

5. **Load balancer**: ALB with HTTPS listener (ACM certificate), path-based routing:
   - `/api/*` → backend target group
   - `/uploads/*` → backend (or S3 + CloudFront)
   - `/*` → S3/CloudFront (frontend SPA)

6. **DNS**: Route53 A record pointing to CloudFront.

7. **Monitoring**: CloudWatch Logs from ECS, CloudWatch Alarms on 5xx rate, RDS Enhanced Monitoring.

### Production Hardening

- Enable RDS automated backups (7-35 day retention)
- Enable Multi-AZ RDS for high availability
- Use ECS Service Auto Scaling (target tracking on CPU)
- Put WAF in front of ALB (rate limiting, SQL injection protection)
- Enable ALB access logs to S3
- Use Secrets Manager for JWT secret and DB credentials
- Set up Sentry for error tracking
- Use CloudFront signed URLs for upload viewing if reports are sensitive

---

## Option C: Bare Metal / VPS

### Prerequisites
- Ubuntu 22.04+ or Debian 12+
- Python 3.11+, Node 20+, PostgreSQL 15 with PostGIS
- nginx
- 2GB+ RAM

### Steps

```bash
# 1. Install system deps
sudo apt update
sudo apt install -y python3.11 python3.11-venv nodejs npm postgresql postgresql-15-postgis-3 nginx

# 2. Set up database
sudo -u postgres createuser infraguard -P
sudo -u postgres createdb infraguard -O infraguard
sudo -u postgres psql -d infraguard -c "CREATE EXTENSION postgis; CREATE EXTENSION pg_trgm;"
psql -U infraguard -d infraguard -f database/schema.sql
psql -U infraguard -d infraguard -f database/seed.sql

# 3. Backend
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit DATABASE_URL, JWT_SECRET_KEY
python -m app.seed  # Seed admin + demo data

# Run with gunicorn + uvicorn workers
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000

# 4. Frontend
cd ../frontend
npm install
npm run build

# 5. nginx config
sudo cp docker/nginx.conf /etc/nginx/sites-available/infraguard
sudo ln -s /etc/nginx/sites-available/infraguard /etc/nginx/sites-enabled/
# Edit /etc/nginx/sites-available/infraguard:
#   - root /home/user/infraguard/frontend/dist;
#   - proxy_pass http://127.0.0.1:8000;
sudo nginx -t && sudo systemctl reload nginx

# 6. SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d infraguard.example.com
```

### Systemd Service (backend)

Create `/etc/systemd/system/infraguard-backend.service`:

```ini
[Unit]
Description=InfraGuard FastAPI Backend
After=network.target postgresql.service

[Service]
User=infraguard
WorkingDirectory=/home/infraguard/backend
Environment="PATH=/home/infraguard/backend/venv/bin"
ExecStart=/home/infraguard/backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable infraguard-backend
sudo systemctl start infraguard-backend
```

---

## Post-Deployment Checklist

- [ ] Change `JWT_SECRET_KEY` from default
- [ ] Change default admin password (`Admin@12345`)
- [ ] Verify HTTPS is enforced
- [ ] Verify CORS allowlist matches your domain
- [ ] Set up automated database backups
- [ ] Set up log rotation
- [ ] Configure firewall (only expose 80/443)
- [ ] Test report submission end-to-end
- [ ] Test admin login and report management
- [ ] Test map loads and filtering works
- [ ] Verify AI model is loaded (check `/health` endpoint)
- [ ] Set up monitoring alerts for 5xx errors
- [ ] Document the deployment location and credentials in a secure vault

## Scaling Considerations

| Component | Current Limit | Scaling Strategy |
|---|---|---|
| Backend (single uvicorn) | ~1000 req/min | Run 4+ uvicorn workers behind gunicorn; horizontally scale with multiple containers |
| Database (single RDS) | ~100 concurrent connections | Use PgBouncer connection pooler; read replicas for analytics queries |
| File uploads (local disk) | Limited by disk size | Move to S3 with presigned URLs for direct browser upload |
| AI inference (sync) | ~50-150ms per image | Background queue (Celery + Redis) for async processing |
| Map rendering (client) | ~10k markers max | Pre-cluster server-side; use vector tiles for very dense areas |
| Notifications (polling) | 1 req per user per 30s | Switch to WebSocket / Server-Sent Events for real-time push |
