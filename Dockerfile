FROM python:3.12-slim

# Install directly into the system Python (no virtualenv needed in containers)
ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONUNBUFFERED=1

# Install Poetry and gosu (for privilege dropping in the entrypoint)
RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry

# Create a non-root user for running the application
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml poetry.lock* ./

# Install runtime dependencies only (no dev deps)
RUN poetry install --no-root --without dev

# Copy the rest of the project
COPY . .

# Ensure models and secrets directories exist, set permissions, and make the entrypoint executable
RUN mkdir -p models .secrets && chmod +x docker-entrypoint.sh && chown -R appuser:appuser /app

# NOTE: USER is intentionally not set here — docker-entrypoint.sh starts as root,
# fixes ownership of bind-mounted volumes, then drops to appuser via gosu.

# models/ is downloaded at startup and .secrets/ stores OAuth tokens; both should be mounted for persistence:
#   docker run -v /path/to/models:/app/models -v /path/to/.secrets:/app/.secrets streamantix
VOLUME ["/app/models", "/app/.secrets"]

# Environment variables must be supplied at runtime, e.g.:
#   docker run --env-file .env streamantix
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "main.py"]
