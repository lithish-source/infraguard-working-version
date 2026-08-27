# Backend Dockerfile — FastAPI + AI module
FROM python:3.11-slim

# System deps for OpenCV, PostGIS client, build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgl1 libglib2.0-0 libpq-dev gdal-bin binutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code + AI module
COPY backend/ /app/backend/
COPY ai/ /app/ai/

WORKDIR /app/backend

# Create uploads + model directories
RUN mkdir -p /app/backend/uploads /app/ai/models /app/ai/data

ENV PYTHONPATH=/app:/app/backend:/app/ai
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run via uvicorn; the app's lifespan hook creates tables and seeds data
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
