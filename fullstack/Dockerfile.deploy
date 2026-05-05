# Production Dockerfile
# Frontend: build static files with Vite
# Backend: serve with FastAPI + uvicorn

FROM node:20-slim AS frontend-build
RUN npm install -g pnpm
WORKDIR /build
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN npx vite build

FROM python:3.12-slim
WORKDIR /app

# uv — fast Python package installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Backend deps (lockfile for deterministic builds)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --no-editable

# Backend code
COPY backend/ ./backend/

# Frontend static files
COPY --from=frontend-build /build/dist ./frontend/dist/

# Serve backend from the backend directory so relative imports work
WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
