FROM python:3.12.4-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY . .
COPY entrypoint.sh /usr/local/bin/employee-tracker-entrypoint

RUN useradd --create-home --shell /bin/bash app && \
    chmod +x /usr/local/bin/employee-tracker-entrypoint && \
    chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8000}/health" || exit 1

ENTRYPOINT ["/usr/local/bin/employee-tracker-entrypoint"]
