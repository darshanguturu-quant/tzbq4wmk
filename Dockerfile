# =============================================================================
# Stage 1: Frontend Build (Node.js LTS)
# =============================================================================
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# =============================================================================
# Stage 2: Runtime Container (Python 3.12 Slim)
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application backend, data snapshot, and compiled frontend assets
COPY backend/ ./backend/
COPY data/ ./data/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Security: run as non-root user
RUN useradd -u 1000 -m appuser && \
    chown -R appuser:appuser /app
USER appuser

# Start FastAPI server listening on dynamic $PORT (Heroku/Docker compatible)
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
