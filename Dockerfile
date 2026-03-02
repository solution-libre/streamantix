FROM python:3.12-slim

# Install directly into the system Python (no virtualenv needed in containers)
ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Install Poetry
RUN pip install --no-cache-dir poetry

# Create a non-root user for running the application
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml poetry.lock* ./

# Install runtime dependencies only (no dev deps)
RUN poetry install --no-root --without dev

# Copy the rest of the project
COPY . .

# Ensure models directory exists, set permissions, and make the entrypoint executable
RUN mkdir -p models && chmod +x docker-entrypoint.sh && chown -R appuser:appuser /app

USER appuser

# models/ is downloaded at startup and should be mounted for persistence:
#   docker run -v /path/to/models:/app/models streamantix
VOLUME ["/app/models"]

# Environment variables must be supplied at runtime, e.g.:
#   docker run --env-file .env streamantix
ENTRYPOINT ["/app/docker-entrypoint.sh"]
