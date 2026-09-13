# Digital Student Attendance System
## Repository Structure Specification

**Document Version:** 1.0  
**Status:** Approved Architectural Baseline  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Overview and Monorepo Philosophy

The Digital Student Attendance System is maintained as a **unified monorepo** containing all application layers, infrastructure definitions, API contracts, cross-system test suites, and architectural governance documentation.

Per **ADR-008 (Monorepo)**, this structure ensures:
1. **Single Source of Truth**: Code, documentation, schemas, and deployment scripts evolve synchronously in atomic commits.
2. **AI Agent Safety**: Coding agents (Codex, Antigravity, Claude Code) maintain full context across client-server boundaries without cross-repository drift.
3. **Consistent Governance**: Centralized linting, type-checking, CI pipelines, and security invariants apply uniformly across the entire stack.

---

## 2. Directory Layout

The repository root is organized as follows:

```text
UniversityAttendaceSystem/
│
├── .github/
│   └── workflows/              # CI/CD automation pipelines (GitHub Actions)
│
├── apps/
│   ├── web/                    # Next.js + TypeScript responsive web application & PWA
│   └── mobile/                 # Flutter mobile application (Android & iOS)
│
├── backend/
│   ├── app/                    # FastAPI modular monolith application source
│   ├── migrations/             # Alembic database migration scripts
│   └── tests/                  # Backend unit, service, and API integration tests
│
├── contracts/                  # OpenAPI specifications, JSON schemas, and generated client types
│
├── infra/
│   ├── docker/                 # Production & development Dockerfiles
│   ├── nginx/                  # Reverse proxy and TLS gateway configurations
│   ├── backup/                 # Campus database automated backup and recovery scripts
│   └── scripts/                # Infrastructure provisioning and maintenance utilities
│
├── docs/                       # Project specifications (00 through 28, ADRs, manifests)
│
├── tests/
│   ├── e2e/                    # End-to-end integration and user-journey tests
│   ├── load/                   # Locust/k6 load and stress simulation tests
│   └── security/               # Automated vulnerability, authorization, and replay tests
│
├── scripts/                    # Developer tooling, environment bootstrap, and utility scripts
│
├── archive/                    # Archived milestone packages and historical reference zips
│
├── AGENTS.md                   # Core operational directives and constraints for AI agents
├── README.md                   # Developer entry point, setup instructions, and architecture map
├── .editorconfig               # Universal cross-platform whitespace and encoding rules
├── .env.example                # Safe environment variable configuration template
├── .gitattributes              # Git line-ending normalization and path filters
├── .gitignore                  # Comprehensive version control ignore definitions
├── docker-compose.yml          # Local campus & development multi-container orchestration
└── LICENSE_PLACEHOLDER.md      # Institutional license and copyright declaration
```

---

## 3. Detailed Component Ownership & Boundaries

### 3.1 `apps/web/` (Next.js PWA)
- **Primary Responsibility**: Web interface and Progressive Web App for Administrators, Lecturers, Deans, Department Heads, System Operators, and Student general self-service (desktop/laptop/tablet/browser).
- **Technology**: Next.js (App Router), React, TypeScript (strict mode), Tailwind CSS.
- **Allowed Content**:
  - UI components, page layouts, client-side route handlers.
  - Localization resources (English, Dari, Pashto) with complete RTL (Right-to-Left) layout support.
  - Server actions and client API fetchers consuming `/api/v1` REST endpoints.
  - Browser-side session management, PWA service worker, and web-compatible local state.
- **Forbidden Content**:
  - **No authoritative attendance business logic**: The web client must never calculate or decide final attendance status.
  - **No direct database queries**: All data access must pass through the FastAPI backend API.
  - **No backend database credentials or signing private keys**: Secrets must never be bundled into client bundles.

### 3.2 `apps/mobile/` (Flutter Native Client)
- **Primary Responsibility**: Native mobile client for Students (attendance check-ins, cryptographic device registration, Bluetooth presence confirmation) and Lecturers (dynamic QR display, Bluetooth beacon broadcasting, attendance management, offline fallback scanning).
- **Technology**: Flutter, Dart (null safety), Riverpod (state management), Drift / SQLite (encrypted local persistence).
- **Allowed Content**:
  - Flutter UI screens, widgets, controllers, and Riverpod providers.
  - Platform channels and plugins for Bluetooth Low Energy (BLE), Wi-Fi network detection, and hardware cryptographic key generation (Secure Enclave / Android Keystore).
  - SQLite/Drift database schema for local offline caching and queueing.
  - Local offline sync queue and payload signing routines.
- **Forbidden Content**:
  - **No final attendance determination**: Mobile client must never mark itself "Present" without backend validation.
  - **No reliance on client device clock**: Device timestamps are recorded as evidence only; server time is strictly authoritative.
  - **No hardcoded API secrets or backend keys**.

### 3.3 `backend/` (FastAPI Modular Monolith)
- **Primary Responsibility**: Core university business logic, identity and role-based access control (RBAC), schedule management, attendance session lifecycle, anti-cheating verification, cryptographic token rotation, and audit ledger.
- **Technology**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0+ (async), Alembic, Celery, Redis.
- **Internal Structure**:
  ```text
  backend/
  ├── app/
  │   ├── main.py               # Application factory, lifespan hooks, and router mounting
  │   ├── core/                 # Configuration, security utilities, database engine, Redis client
  │   ├── common/               # Shared domain exceptions, pagination, standard API response envelopes
  │   └── modules/              # Domain modules (modular monolith architecture)
  │       ├── identity/         # Users, roles, permissions, authentication, JWT tokens
  │       ├── academic/         # Universities, academic units, years, semesters, sections
  │       ├── courses/          # Courses, course offerings, lecturer assignments, enrollments
  │       ├── scheduling/       # Rooms, timetables, class occurrences
  │       ├── attendance/       # Sessions, checkpoints, evidence validation, final records
  │       ├── devices/          # Cryptographic device registration and approval
  │       ├── sync/             # Transactional outbox, cloud synchronization engine
  │       ├── audit/            # Immutable audit logging and security event tracking
  │       └── reports/          # Attendance statistics, export generators (PDF, Excel)
  ├── migrations/               # Alembic version scripts and environment configuration
  └── tests/                    # Unit, module, and integration test suites
  ```
- **Allowed Content**:
  - Domain models, service layer business logic, schemas, and REST route controllers.
  - Database migrations, seed data scripts, and Celery background task handlers.
- **Forbidden Content**:
  - **No presentation/HTML rendering**: Backend serves pure JSON over REST (`/api/v1`).
  - **No cross-module direct database joins that violate bounded contexts**: Modules communicate via service interfaces.

### 3.4 `contracts/` (API Contracts & Schemas)
- **Primary Responsibility**: Single source of truth for client-server interface definitions.
- **Allowed Content**:
  - Generated OpenAPI 3.1 JSON/YAML specifications extracted from FastAPI routes.
  - JSON schemas for offline sync outbox payloads and cryptographic token payloads.
  - TypeScript types and Dart models generated from the OpenAPI specification.
- **Rule**: Web and mobile clients generate their network models from these contracts to prevent API drift.

### 3.5 `infra/` (Infrastructure & Deployment)
- **Primary Responsibility**: Containerization, local server orchestration, reverse proxy configuration, and campus backup routines.
- **Allowed Content**:
  - `docker/`: Dockerfiles for backend, celery worker, and web PWA.
  - `nginx/`: Nginx configuration files handling HTTPS, WebSocket/SSE proxying, static asset caching, and rate limiting.
  - `backup/`: PostgreSQL automated daily backup, WAL archiving, and restore test scripts.
  - `scripts/`: Campus host operating system provisioning and maintenance scripts.
- **Forbidden Content**:
  - No application business logic.
  - No production passwords or private keys.

### 3.6 `docs/` (Architecture & Requirement Specifications)
- **Primary Responsibility**: Permanent architectural, business, and operational truth.
- **Allowed Content**: Documents `00` through `28`, ADRs, and milestone audit manifests.
- **Rule**: Changes to system behavior require prior approval and updates to documentation.

### 3.7 `tests/` (System-Wide & Specialized Testing)
- **Primary Responsibility**: Non-functional, cross-cutting, and end-to-end verification.
- **Subdirectories**:
  - `e2e/`: Playwright end-to-end tests validating full user workflows across Web and Backend.
  - `load/`: Locust/k6 scripts simulating 500+ concurrent students scanning QR codes within a 3-minute window.
  - `security/`: Penetration testing scripts, QR replay simulators, spoofing tests, and token tamper checks.

---

## 4. Rules Preventing Business Logic Duplication

1. **Server-Authoritative Invariant**:
   - The attendance decision engine exists **only** in `backend/app/modules/attendance/services/`.
   - Neither `apps/web/` nor `apps/mobile/` may implement attendance decision logic (such as calculating whether a student meets the 75% attendance threshold or evaluating 2-of-3 checkpoints). Clients solely display results computed by the backend.

2. **Single Contract Pipeline**:
   - DTOs (Data Transfer Objects) originate in `backend/app/modules/*/schemas.py`.
   - They are exported to `contracts/openapi.json`.
   - Client models in TypeScript and Dart are generated from `contracts/` rather than manually maintained.

3. **Domain Validation Authority**:
   - Client-side validation is strictly for immediate user experience (e.g., non-empty form fields).
   - All authorization, business constraints, schedule adherence, and cryptographic checks are enforced server-side.
