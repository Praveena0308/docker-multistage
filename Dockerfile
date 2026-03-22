#stage 1
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY ./app/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --prefix=/install -r /app/requirements.txt

#stage 2 tester

FROM builder AS tester

WORKDIR /tests

COPY --from=builder  /install /usr/local

COPY app/ ./app/
COPY tests/ ./tests/

RUN cd /tests && python -m pytest tests/ -v 

#stage 3 runner

FROM python:3.12-slim AS runner

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup  --no-create-home appuser


WORKDIR /app

COPY --from=builder /install /usr/local

COPY app/ .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

# Environment variables with defaults
ENV APP_ENV=production \
    APP_VERSION=1.0.0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# HEALTHCHECK — Docker and Kubernetes use this
# --interval: check every 30 seconds
# --timeout: fail if no response in 5 seconds
# --start-period: wait 10s before first check (app startup time)
# --retries: 3 failures = unhealthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8080/health', timeout=4); exit(0 if r.status_code==200 else 1)"

# Start the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--workers", "1", "--access-log"]