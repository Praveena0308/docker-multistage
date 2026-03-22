# Day 2 — Multi-Stage Docker Build

> **30-Day DevOps Challenge** | Day 2 of 30

A production-grade Python FastAPI container built using Docker multi-stage builds — demonstrating how real companies reduce image size, enforce security, and ensure code quality through containerized testing.


## Tools Used

`Docker` · `Python 3.12` · `FastAPI` · `uvicorn` · `pytest` · `Docker Compose`

---
## What This Project Covers

- Multi-stage Docker builds — builder → tester → runner pattern
- Build cache optimization — `requirements.txt` copied before source code
- Containerized testing — pytest runs inside Docker, broken code never reaches production
- Docker HEALTHCHECK — enables Kubernetes liveness and readiness probes
- Non-root container user — security best practice, least privilege principle
- `.dockerignore` — prevents secrets and unnecessary files entering build context
- Environment variable injection — runtime config without hardcoding
- Docker Compose — local development with separate test profile

---

## Project Structure

```
day02-docker-multistage/
├── app/
│   ├── main.py              # FastAPI application
│   └── requirements.txt     # Python dependencies
├── tests/
│   └── test_app.py          # pytest test suite
├── Dockerfile               # Multi-stage production build
├── docker-compose.yml       # Local development setup
├── .dockerignore            # Prevents secrets/cache in build context
└── README.md
```

---

## Architecture — How Multi-Stage Build Works

```
┌─────────────────────────────────────────────────────────┐
│                    Dockerfile                           │
│                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │
│  │  STAGE 1    │   │  STAGE 2    │   │  STAGE 3    │  │
│  │  builder    │──►│  tester     │──►│  runner     │  │
│  │             │   │             │   │             │  │
│  │ gcc         │   │ pytest runs │   │ packages ✅ │  │
│  │ pip install │   │ tests pass? │   │ app code ✅ │  │
│  │ packages    │   │ yes → next  │   │ appuser  ✅ │  │
│  │             │   │ no → STOP   │   │             │  │
│  └─────────────┘   └─────────────┘   └─────────────┘  │
│   thrown away        thrown away       FINAL IMAGE     │
│   ~900MB             ~900MB            ~120MB          │
└─────────────────────────────────────────────────────────┘
```

**Key insight:** Only Stage 3 becomes the final image. Stages 1 and 2 are thrown away. This is why the final image is 8x smaller — no build tools, no test frameworks, no pip, no gcc.

---

## Prerequisites

```bash
docker --version
docker compose version
```

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/praveena0308/day02-docker-multistage
cd day02-docker-multistage

# Build the multi-stage image
docker build -t devops-api:latest .

# Run the container
docker run -d \
  --name devops-api \
  -p 8080:8080 \
  -e APP_ENV=production \
  -e APP_VERSION=1.0.0 \
  devops-api:latest

# Test it is running
curl http://localhost:8080/health
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Root — API info and links |
| GET | `/health` | Health check — used by Docker and Kubernetes |
| GET | `/items` | List all items |
| POST | `/items/{key}` | Create an item |
| GET | `/items/{key}` | Get a specific item |
| DELETE | `/items/{key}` | Delete an item |
| GET | `/docs` | Auto-generated Swagger UI |

### Example Requests

```bash
# Health check
curl http://localhost:8080/health

# Create an item
curl -X POST http://localhost:8080/items/server1 \
  -H "Content-Type: application/json" \
  -d '{"name": "prod-server", "value": "192.168.1.10"}'

# List all items
curl http://localhost:8080/items

# Get specific item
curl http://localhost:8080/items/server1

# Test 404 error handling
curl http://localhost:8080/items/nonexistent

# Delete an item
curl -X DELETE http://localhost:8080/items/server1
```

### Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "version": "1.0.0",
  "environment": "production",
  "hostname": "0042b9f6d971",
  "python": "3.12.0"
}
```

---

## Dockerfile Explained

### Stage 1 — Builder

```dockerfile
FROM python:3.12-slim AS builder

WORKDIR /build

# Install gcc — needed to compile Python packages with C extensions
# rm -rf in same RUN command — prevents cache being saved as a layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements FIRST — Docker caches this layer
# If requirements.txt has not changed, pip install is skipped on rebuild
COPY app/requirements.txt .

# --prefix=/install puts packages in isolated folder
# Makes it easy to copy ONLY packages to the next stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
```

### Stage 2 — Tester

```dockerfile
FROM builder AS tester

WORKDIR /test

COPY --from=builder /install /usr/local

COPY app/ ./app/
COPY tests/ ./tests/

# If tests fail, build stops here
# Broken code NEVER reaches the final image
RUN python -m pytest tests/ -v
```

### Stage 3 — Runner

```dockerfile
FROM python:3.12-slim AS runner

# Create non-root user — running as root is a security risk
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Copy packages from /install to /usr/local
# Python finds packages in /usr/local/lib/python3.12/site-packages/
COPY --from=builder /install /usr/local

COPY app/ .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

ENV APP_ENV=production \
    APP_VERSION=1.0.0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8080/health', timeout=4); exit(0 if r.status_code==200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--workers", "1", "--access-log"]
```

## Docker Compose

```bash
# Start in development mode
docker compose up -d

# Run tests only
docker compose --profile test run test

# Follow logs
docker compose logs -f

# Stop everything
docker compose down
```

---

## Security Verification

```bash
# Should return "appuser" not "root"
docker exec devops-api whoami

# Verify no secrets leaked into image
docker run --rm devops-api:latest find / -name ".env" 2>/dev/null

# Check UID and GID
docker exec devops-api id
# uid=1001(appuser) gid=1001(appgroup)
```

---

## Health Check Verification

```bash
# Check health status
docker inspect devops-api --format '{{.State.Health.Status}}'
# Output: healthy

# docker ps shows health status inline
docker ps
# STATUS: Up 5 minutes (healthy)
```

---


---


**uvicorn: executable file not found**

This means the COPY path has a typo in Stage 3 of your Dockerfile:
```dockerfile
# Correct
COPY --from=builder /install /usr/local

# Wrong — /user/local does not exist
COPY --from=builder /install /user/local
```

**Tests failing in tester stage**
```bash
docker build --no-cache -t devops-api:latest .
```

---

## Key Concepts Learned

**Multi-stage builds** — Multiple `FROM` instructions in one Dockerfile. Each stage can copy from previous stages. Only the final stage becomes the image.

**Build cache** — Docker caches each layer. Copying `requirements.txt` before `COPY . .` means pip install is skipped when only code changes. Faster rebuilds.

**`--prefix=/install`** — Installs pip packages into an isolated folder. Makes it easy to copy only packages to the next stage without touching system files.

**Non-root user** — Security best practice. Limits blast radius if the app is exploited.

**HEALTHCHECK** — Docker periodically runs this command. 3 failures = container marked unhealthy. Kubernetes uses this for liveness probes.

**`.dockerignore`** — Keeps secrets out of images and speeds up builds.



*Built as part of a 30-day DevOps portfolio challenge targeting the German job market.*