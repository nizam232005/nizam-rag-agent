FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy app source
COPY *.py ./

# Expose port (Railway sets $PORT)
EXPOSE 8000

# Run FastAPI with uvicorn
CMD uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
