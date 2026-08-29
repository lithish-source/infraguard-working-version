# Stage 1: Build the React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend with built Frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code and ai modules
COPY backend /app
COPY ai /app/ai

# Copy built frontend assets from stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend_dist

# Default environment settings
ENV DATABASE_URL="sqlite:///./infraguard.db"
ENV UPLOAD_DIR="/tmp/uploads"
ENV FRONTEND_DIST="/app/frontend_dist"
ENV PORT=8000

RUN mkdir -p /tmp/uploads

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
