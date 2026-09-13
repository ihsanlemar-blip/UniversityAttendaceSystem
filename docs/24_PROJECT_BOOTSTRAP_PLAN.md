# Digital Student Attendance System
## Project Bootstrap Plan

**Document Version:** 1.0  
**Status:** Approved Operational Guide  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Objective and Scope

This document specifies the exact sequence of 16 engineering steps required to transition the Digital Student Attendance System from documentation specifications into an active, testable development repository.

### Scope Rule
> [!IMPORTANT]
> The bootstrap creates the **infrastructure and scaffolding baseline only**. It must not implement business logic, authentication models, attendance sessions, QR algorithms, or full domain features. Those belong to Milestone 4 and subsequent milestones.

---

## 2. The 16-Step Bootstrap Sequence

```text
  [1] Git Init & Config ──────► [2] Monorepo Layout ──────► [3] Bootstrap FastAPI
                                                                     │
  [6] Add PostgreSQL ◄───────── [5] Bootstrap Flutter ◄──── [4] Bootstrap Next.js
        │
        ▼
  [7] Add Redis ──────────────► [8] Add Celery ───────────► [9] Docker Compose
                                                                     │
  [12] Add Formatting ◄──────── [11] Add Linting ◄───────── [10] Health Checks
        │
        ▼
  [13] Test Frameworks ───────► [14] CI Pipelines ────────► [15] API Contracts
                                                                     │
                                [16] Baseline Commit ◄───────────────┘
```

### Step 1: Initialize Git and Base Attributes
- Initialize Git repository on `main` branch.
- Create `.gitignore`, `.gitattributes`, and `.editorconfig`.
- Configure line-ending normalization (LF for code, CRLF allowed for Windows batch files).

### Step 2: Create Monorepo Directory Layout
- Create core directories: `apps/web/`, `apps/mobile/`, `backend/app/`, `backend/migrations/`, `backend/tests/`, `contracts/`, `infra/docker/`, `infra/nginx/`, `infra/backup/`, `infra/scripts/`, `tests/e2e/`, `tests/load/`, `tests/security/`, `scripts/`.
- Ensure directory purposes are established with minimal `.gitkeep` or package configuration files.

### Step 3: Bootstrap FastAPI Backend Skeleton
- Create `backend/pyproject.toml` or `requirements.txt` declaring FastAPI, Pydantic, Uvicorn, and Starlette.
- Create `backend/app/main.py` with FastAPI instance and metadata.
- Expose `/health/live` (liveness probe: returns `{"status": "alive"}`).
- Expose `/health/ready` (readiness probe: validates basic runtime readiness).

### Step 4: Bootstrap Next.js Web Shell
- Initialize minimal Next.js application shell inside `apps/web/`.
- Configure `package.json`, `tsconfig.json`, `next.config.js`.
- Provide minimal health check route or layout confirming Next.js build readiness.

### Step 5: Bootstrap Flutter Mobile Shell
- Initialize minimal Flutter package inside `apps/mobile/`.
- Configure `pubspec.yaml` with application ID `com.university.attendance`.
- Create entrypoint `lib/main.py` (or `lib/main.dart`) rendering minimal placeholder shell.

### Step 6: Configure PostgreSQL Database Layer
- Define PostgreSQL 16 service in `docker-compose.yml` with named volume `postgres_data`.
- Configure async database connection URL in `.env.example`.
- Scaffold Alembic migration directory `backend/migrations/` with `alembic.ini`.

### Step 7: Configure Redis Transient State Layer
- Define Redis 7 service in `docker-compose.yml` with health check (`redis-cli ping`).
- Configure Redis URL in `.env.example`.

### Step 8: Configure Celery Background Worker
- Declare Celery dependency in backend configuration.
- Define `worker` service in `docker-compose.yml` sharing backend source mount.

### Step 9: Orchestrate with Docker Compose
- Assemble all services (`postgres`, `redis`, `backend`, `worker`, `web`) into root `docker-compose.yml`.
- Enforce network isolation on `attendance-net`.
- Configure container health checks and dependencies.

### Step 10: Implement Multi-Tier Health Checks
- Implement backend `/health/live` (HTTP 200).
- Implement backend `/health/ready` (checks DB and Redis reachability when connected).
- Implement web route `/api/health` returning application status.

### Step 11: Configure Code Linting
- Backend: Configure Ruff in `pyproject.toml` (rules: E, F, I, B, S).
- Web: Configure ESLint in `apps/web/.eslintrc.json`.
- Mobile: Configure `analysis_options.yaml` in `apps/mobile/`.

### Step 12: Configure Code Formatting
- Backend: Ruff formatter (`line-length = 100`).
- Web: Prettier (`tabWidth: 2`, `singleQuote: true`).
- Mobile: `dart format`.

### Step 13: Add Automated Test Frameworks
- Backend: Configure `pytest` with `pytest-asyncio` and `pytest-cov` in `backend/tests/`.
- Web: Configure Vitest or Jest in `apps/web/`.
- Mobile: Configure Flutter test suite in `apps/mobile/test/`.

### Step 14: Add CI Automation Pipeline
- Create `.github/workflows/ci.yml` defining automated test jobs for backend, web, mobile, and security scans.

### Step 15: Establish API Contract Pipeline
- Create `contracts/README.md` defining the OpenAPI export workflow from FastAPI into TypeScript and Dart types.

### Step 16: Review, Validate, and Commit Baseline
- Execute full linting and health check verification.
- Verify `git status` contains no untracked secrets or extraneous binaries.
- Create initial Git commit: `feat(repo): [TASK-001-09] milestone 3 repository bootstrap baseline`.

---

## 3. Bootstrap Acceptance Criteria

The bootstrap is declared complete when:
1. `docker-compose.yml` config is syntactically valid and free of errors.
2. `backend/app/main.py` boots and responds to `/health/live` with HTTP 200 OK.
3. `apps/web/` compiles under TypeScript strict mode.
4. `apps/mobile/` passes static analysis without syntax errors.
5. All 16 approved Milestone 1 & 2 documents remain intact in `docs/`.
6. Zero secrets exist in the repository tree.
