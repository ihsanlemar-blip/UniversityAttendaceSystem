# Digital Student Attendance System
## Docker and Local Campus Infrastructure Specification

**Document Version:** 1.0  
**Status:** Approved Infrastructure Architecture  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Architectural Context

Per **ADR-002 (Campus Server Is Operational Authority)** and **ADR-020 (Dockerized Local Deployment)**, the system runs on a university campus server inside Docker containers. Internet connectivity to the cloud is neither assumed nor required for daily attendance capture.

This document defines:
1. The **Local Development Environment** orchestrated via Docker Compose.
2. The **Campus Production Server Topology** with hardened reverse proxy, backup agents, and isolated network segments.

---

## 2. Local Development Services

The development container cluster defined in `docker-compose.yml` provides a self-contained local environment:

```text
┌─────────────────────────────────────────────────────────────┐
│                   Local Developer Host                      │
│                                                             │
│   ┌───────────────┐     ┌───────────────┐                   │
│   │   apps/web    │     │ backend/app   │                   │
│   │ (Next.js PWA) │     │ (FastAPI API) │                   │
│   │   Port 3000   │     │   Port 8000   │                   │
│   └───────┬───────┘     └───────┬───────┘                   │
│           │                     │                           │
│           ▼                     ▼                           │
│   ┌─────────────────────────────────────┐                   │
│   │    Docker Network: attendance-net   │                   │
│   └──────┬──────────────────────┬───────┘                   │
│          │                      │                           │
│          ▼                      ▼                           │
│   ┌──────────────┐      ┌──────────────┐    ┌─────────────┐ │
│   │  PostgreSQL  │      │    Redis     │    │   Celery    │ │
│   │  (Port 5432) │      │  (Port 6379) │    │   Worker    │ │
│   └──────────────┘      └──────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Service Definitions

| Service | Image / Base | Internal Port | Host Port | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `postgres` | `postgres:16-alpine` | `5432` | `5432` | Primary relational database. Persistent data stored in named volume `postgres_data`. |
| `redis` | `redis:7-alpine` | `6379` | `6379` | In-memory cache, dynamic token session store, and Celery message broker. |
| `backend` | Python 3.12 (Dockerfile) | `8000` | `8000` | FastAPI modular monolith backend application. Hot reloads code via volume mount. |
| `worker` | Python 3.12 (Dockerfile) | N/A | N/A | Celery background task worker for asynchronous jobs (emails, imports, sync). |
| `web` | Node.js 20 (Dockerfile) | `3000` | `3000` | Next.js responsive web application and PWA development server. |

*Note: Mobile Flutter client runs outside Docker on the developer workstation or test device/emulator, communicating with `backend` at `http://localhost:8000/api/v1` (or `http://10.0.2.2:8000/api/v1` for Android emulator).*

---

## 3. Container Startup Order & Health Checks

To prevent race conditions during cold boot, services enforce strict dependencies with health checks:

```text
postgres (healthy) ──┐
                     ├──► backend (healthy) ──► web
redis (healthy)    ──┤
                     └──► worker
```

1. **`postgres` Health Check**:
   ```yaml
   test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER:-attendance_user} -d ${DATABASE_NAME:-attendance_db}"]
   interval: 5s
   timeout: 5s
   retries: 5
   ```
2. **`redis` Health Check**:
   ```yaml
   test: ["CMD", "redis-cli", "ping"]
   interval: 5s
   timeout: 5s
   retries: 5
   ```
3. **`backend` Health Check**:
   ```yaml
   test: ["CMD-SHELL", "curl -f http://localhost:8000/health/ready || exit 1"]
   interval: 10s
   timeout: 5s
   retries: 3
   ```
4. **`web` and `worker` Dependency Rule**:
   - `backend` starts only after `postgres` and `redis` are `healthy`.
   - `worker` starts only after `backend` and `redis` are ready.
   - `web` starts after `backend` is operational.

---

## 4. Networks & Volumes

### Networks
- `attendance-net`: Internal bridge network (`driver: bridge`). All inter-service traffic (FastAPI to PostgreSQL, Celery to Redis) occurs strictly across this private virtual network.

### Persistent Volumes
- `postgres_data`: Named volume mounting `/var/lib/postgresql/data` ensuring database records persist across container restarts.
- `redis_data`: Named volume mounting `/data` preserving transient state snapshots.
- `backup_data`: Mount directory `/var/backups/attendance` storing automated database dumps.

---

## 5. Campus Production Infrastructure Concept

In a university campus deployment, the topology expands to include an Nginx reverse proxy gateway, automated backup agent, and local network security isolation:

```text
               Campus LAN (Wi-Fi & Ethernet)
                             │
                             ▼ (Port 80/443)
┌─────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                      │
│        (TLS 1.3 Termination, Rate Limiting, Static PWA)     │
└─────────────┬───────────────────────────────┬───────────────┘
              │ (HTTP 8000)                   │ (HTTP 3000)
              ▼                               ▼
      ┌───────────────┐               ┌───────────────┐
      │ FastAPI Core  │               │  Next.js PWA  │
      └───────┬───────┘               └───────────────┘
              │
  ┌───────────┴───────────┬───────────────────────┐
  │                       │                       │
  ▼                       ▼                       ▼
┌──────────────┐  ┌──────────────┐        ┌──────────────┐
│  PostgreSQL  │  │    Redis     │        │    Celery    │
│  (Isolated)  │  │  (Isolated)  │        │    Worker    │
└──────┬───────┘  └──────────────┘        └──────────────┘
       │
       ▼
┌──────────────┐
│ Backup Agent │ (Daily pg_dump + WAL archiving to local NAS)
└──────────────┘
```

### Production Security Boundaries
1. **No External Database Exposure**: In production, PostgreSQL port `5432` and Redis port `6379` are **NEVER** exposed to the campus network. Only the `backend` and `worker` containers communicate with them over the internal bridge network.
2. **Nginx Ingress**: The only ports open to the university campus LAN are `80` (redirected to `443`) and `443` (HTTPS with institutional TLS certificate).
3. **Automated Campus Backups**: The `backup-agent` container runs nightly at 02:00 UTC, performing a consistent `pg_dump` with checksum validation and compressing the archive into `/var/backups/attendance/`.
