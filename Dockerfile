FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code and ai modules
COPY backend /app
COPY ai /app/ai

# Default environment settings
ENV DATABASE_URL="sqlite:///./infraguard.db"
ENV UPLOAD_DIR="/tmp/uploads"
ENV PORT=8000

RUN mkdir -p /tmp/uploads

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
