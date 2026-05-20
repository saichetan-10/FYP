FROM python:3.11-slim

WORKDIR /app

# System deps: gcc for psycopg2 build, postgresql-client for pg_isready, curl for healthcheck
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install only the packages the API actually needs
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy application code
COPY . .

# Make startup script executable
RUN chmod +x docker/start_api.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# start_api.sh: waits for postgres → seeds DB on first run → starts uvicorn
CMD ["bash", "docker/start_api.sh"]
