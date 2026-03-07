FROM python:3.14-slim

WORKDIR /app

RUN pip install uv

# Copy workspace root (pyproject.toml + uv.lock) and backend package
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/
RUN uv sync --frozen --package backend

# Copy backend source
COPY backend/ backend/

WORKDIR /app/backend

EXPOSE 8000
