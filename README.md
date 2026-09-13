# Digital Student Attendance System

An enterprise-grade, offline-resilient, anti-cheating digital student attendance and academic session governance platform engineered for universities.

---

## Current Status & Milestone

- **Current Status**: `Pre-implementation / Repository Bootstrap Complete`
- **Current Milestone**: `Milestone 3 — Repository & Implementation Blueprint`
- **Next Milestone**: `Milestone 4 — Core Foundation & Authentication`

> [!NOTE]
> This repository is currently at the completion of **Milestone 3**. The repository layout, governance frameworks, architectural specifications, database migration roadmaps, CI/CD pipelines, and minimal bootstrap scaffolding are established. Real business functionality (attendance sessions, dynamic tokens, device registration, reports) will be implemented starting in Milestone 4.

---

## Architecture Summary

Per the approved Architecture Decision Records ([docs/15_ARCHITECTURE_DECISIONS.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/15_ARCHITECTURE_DECISIONS.md)):

- **Backend**: FastAPI (Python 3.12+) structured as a modular monolith.
- **Database**: PostgreSQL 16 with UUIDv7 primary keys and UTC timestamps.
- **Cache & Message Broker**: Redis 7 with Celery background workers.
- **Web Portal / PWA**: Next.js (App Router, TypeScript strict mode, Tailwind CSS) with full Right-to-Left (RTL) localization support.
- **Mobile Client**: Flutter (Dart null-safety, Riverpod state management, encrypted Drift / SQLite local storage).
- **Primary Operational Authority**: University campus local server. Cloud is strictly used for asynchronous disaster recovery replication. The system functions fully offline within campus local area networks.
- **Anti-Cheating Engine**:
  - Three-checkpoint attendance model (Start, Middle, End).
  - Dynamic HMAC-SHA256 rotating tokens (20–30s rotation).
  - Cryptographic asymmetric device binding (hardware Keystore / Secure Enclave).
  - Bluetooth Low Energy (BLE) presence beacon verification.
  - Staff-scanned physical QR card fallback.

---

## Repository Map

```text
UniversityAttendaceSystem/
├── apps/
│   ├── web/                    # Next.js responsive web application & PWA
│   └── mobile/                 # Flutter native mobile app (Android & iOS)
├── backend/
│   ├── app/                    # FastAPI modular monolith application
│   ├── migrations/             # Alembic database migrations
│   └── tests/                  # Pytest unit and integration test suite
├── contracts/                  # OpenAPI specifications and client types
├── infra/
│   ├── docker/                 # Production Dockerfiles
│   ├── nginx/                  # Reverse proxy gateway & TLS configs
│   ├── backup/                 # Campus automated database backup scripts
│   └── scripts/                # Infrastructure provisioning scripts
├── docs/                       # Authoritative specifications (00 through 28, ADRs)
├── tests/
│   ├── e2e/                    # Playwright end-to-end integration tests
│   ├── load/                   # Locust/k6 load & stress simulation tests
│   └── security/               # Security & penetration test suites
├── scripts/                    # Developer setup & orchestration scripts
├── archive/                    # Historical milestone reference packages
├── .github/workflows/          # GitHub Actions CI/CD automation pipelines
├── AGENTS.md                   # Operational directives for AI coding agents
├── .editorconfig               # Cross-platform whitespace standards
├── .env.example                # Safe environment variable template
├── .gitattributes              # Git line-ending normalization
├── .gitignore                  # Source control ignore rules
├── docker-compose.yml          # Multi-container local development stack
└── LICENSE_PLACEHOLDER.md      # Institutional copyright and license notice
```

---

## Development Prerequisites

Ensure your host workstation has the following tools installed:
- **Git** (version 2.40+)
- **Python** (version 3.12+)
- **Node.js** (version 20+ LTS) and **npm**
- **Flutter SDK** (channel `stable`, 3.20+)
- **Docker Desktop** / **Docker Engine** and **Docker Compose v2** (optional on bare metal; required for containerized stack)

---

## Getting Started (Local Development)

### 1. Clone & Configure Environment
```bash
cp .env.example .env
```
*(Review and customize values in `.env` as needed. Dev defaults work out of the box.)*

### 2. Start Infrastructure Containers (Docker)
```bash
docker compose up -d postgres redis
```

### 3. Start Backend Application
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Probe: `http://localhost:8000/health/live`

### 4. Start Web Application (PWA)
```bash
cd apps/web
npm install
npm run dev
```
- Web Portal: `http://localhost:3000`

### 5. Start Mobile Client (Flutter)
```bash
cd apps/mobile
flutter pub get
flutter run
```

---

## Architectural Documentation

The `docs/` directory is the single architectural source of truth:
- [00_PROJECT_VISION.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/00_PROJECT_VISION.md)
- [01_PRODUCT_REQUIREMENTS_PRD.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/01_PRODUCT_REQUIREMENTS_PRD.md)
- [04_ATTENDANCE_RULES.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/04_ATTENDANCE_RULES.md)
- [05_ANTI_CHEATING_AND_PRESENCE_MODEL.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md)
- [07_SYSTEM_ARCHITECTURE.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/07_SYSTEM_ARCHITECTURE.md)
- [09_DATABASE_SCHEMA.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/09_DATABASE_SCHEMA.md)
- [15_ARCHITECTURE_DECISIONS.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/15_ARCHITECTURE_DECISIONS.md)
- [16_REPOSITORY_STRUCTURE.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/16_REPOSITORY_STRUCTURE.md)
- [17_IMPLEMENTATION_ROADMAP.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/17_IMPLEMENTATION_ROADMAP.md)
- [18_EPICS_AND_BACKLOG.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/18_EPICS_AND_BACKLOG.md)
- [26_DEFINITION_OF_DONE.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/26_DEFINITION_OF_DONE.md)
- [28_FIRST_IMPLEMENTATION_TASK.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/28_FIRST_IMPLEMENTATION_TASK.md)

---

## AI Agent & Contribution Directives

All AI agents and human contributors must comply with [AGENTS.md](file:///e:/01_Projects/UniversityAttendaceSystem/AGENTS.md) and [docs/13_AGENT_DEVELOPMENT_RULES.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/13_AGENT_DEVELOPMENT_RULES.md).
Key invariant: **The client never marks itself present; all final attendance evaluations are server-authoritative.**
