FROM python:3.12-slim

# Install Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock* ./

# Install runtime dependencies only (no dev deps)
RUN poetry install --no-root --without dev

# Copy the rest of the project
COPY . .

# models/ is not versioned; mount it as a volume at runtime:
#   docker run -v /path/to/models:/app/models streamantix
VOLUME ["/app/models"]

# Environment variables must be supplied at runtime, e.g.:
#   docker run --env-file .env streamantix
CMD ["poetry", "run", "python", "main.py"]
