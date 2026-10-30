# ----------------------------------------------------
# Stage 1: Build React Frontend
# ----------------------------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /build/ui
COPY ui/package*.json ./
RUN npm ci --silent || npm install
COPY ui/ ./
RUN npm run build

# ----------------------------------------------------
# Stage 2: Python Backend Runtime with FFmpeg
# ----------------------------------------------------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# Install FFmpeg and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application backend code
COPY app/ ./app/

# Copy built React frontend assets from Stage 1
COPY --from=frontend-builder /build/ui/dist ./ui/dist

# Ensure storage directories exist
RUN mkdir -p /app/artifacts /app/output

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
