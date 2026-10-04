# syntax=docker/dockerfile:1
#
# Card Catalog — one image, one process, one origin.
#
# Stage 1 builds the React frontend, stage 2 resolves the backend's Python
# dependencies with uv, and the runtime stage is a slim Python image that
# serves the API under /api *and* the built frontend (FastAPI mounts it via
# FRONTEND_DIST — see backend/app/main.py). Neither Node nor uv ships in the
# final image.
#
# Database migrations are NOT run on container start: they're a separate,
# explicit step (`alembic upgrade head`, same image, different command) — the
# `migrate` service in docker-compose.yml locally, a pre-deploy step in
# .github/workflows/deploy.yml in production. See docs/deployment.md.

# --- Stage 1: frontend build ---------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: backend dependencies ----------------------------------------
FROM python:3.13-slim AS backend-deps
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
# --frozen: fail if uv.lock is out of date rather than silently re-resolving.
# --no-dev: pytest & co. stay out of the production image.
RUN uv sync --frozen --no-dev --no-install-project

# --- Stage 3: runtime ---------------------------------------------------------
FROM python:3.13-slim AS runtime
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app \
    && chown app:app /app
WORKDIR /app

COPY --from=backend-deps /app/.venv /app/.venv
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY backend/scripts ./scripts
COPY backend/app ./app
COPY --from=frontend /frontend/dist ./frontend-dist

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/frontend-dist

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

# --proxy-headers: trust X-Forwarded-For from the reverse proxy / load
# balancer in front, so the login rate limiter keys on the real client IP
# rather than the proxy's.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
