# Digital Student Attendance System
## Continuous Integration and Quality Pipeline (CI/CD)

**Document Version:** 1.0  
**Status:** Approved Engineering Automation Policy  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. CI/CD Philosophy and Invariants

To maintain enterprise-grade reliability and prevent regression in security, attendance invariants, or architectural boundaries:
1. **Zero Failing Checks on Main**: Pull requests cannot be merged unless all automated matrix jobs pass with 100% success.
2. **No Fake or Skipped Steps**: CI steps must execute real linters, typecheckers, and test runners; placeholder passes are prohibited.
3. **No Automatic Production Deployment**: Deployments to campus operational servers require explicit human signoff and release verification. Continuous Deployment (CD) into production is intentionally disallowed.

---

## 2. GitHub Actions CI Matrix Overview

The primary CI pipeline (`.github/workflows/ci.yml`) triggers on every Pull Request targeting `main` and on pushes to `main`:

```text
                                GitHub Actions Workflow
                                           │
         ┌──────────────────┬──────────────┴─────┬──────────────────┐
         │                  │                    │                  │
         ▼                  ▼                    ▼                  ▼
┌─────────────────┐┌─────────────────┐  ┌─────────────────┐┌─────────────────┐
│ Backend Checks  ││   Web Checks    │  │  Mobile Checks  ││ Security Checks │
│  - Ruff Format  ││  - ESLint       │  │  - dart format  ││  - Secret Scan  │
│  - Ruff Lint    ││  - TypeScript   │  │  - flutter test ││  - Docker Build │
│  - MyPy Types   ││  - Vitest / Jest│  │  - flutter      ││  - Doc Integrity│
│  - Pytest Suite ││  - Next.js Build│  │    analyze      ││                 │
│  - Alembic Check││                 │  │                 ││                 │
└─────────────────┘└─────────────────┘  └─────────────────┘└─────────────────┘
```

---

## 3. Detailed Pipeline Specifications

### 3.1 Backend Job (`backend-ci`)
- **Runner**: `ubuntu-latest`
- **Services**: PostgreSQL 16, Redis 7
- **Steps**:
  1. Checkout repository.
  2. Setup Python 3.12 with caching (`~/.cache/pip`).
  3. Install dependencies: `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`.
  4. Code Formatting & Linting:
     ```bash
     ruff format --check backend/
     ruff check backend/
     ```
  5. Static Type Checking:
     ```bash
     mypy backend/app
     ```
  6. Database Migration Validation:
     ```bash
     alembic -c backend/alembic.ini check
     ```
  7. Automated Test Suite Execution:
     ```bash
     pytest backend/tests --cov=backend/app --cov-report=xml --cov-fail-under=85
     ```

### 3.2 Web Application Job (`web-ci`)
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout repository.
  2. Setup Node.js 20 with npm caching.
  3. Install dependencies: `npm --prefix apps/web ci`.
  4. Code Linting:
     ```bash
     npm --prefix apps/web run lint
     ```
  5. Strict TypeScript Checking:
     ```bash
     npm --prefix apps/web run type-check
     ```
  6. Unit / Component Testing:
     ```bash
     npm --prefix apps/web test
     ```
  7. Production Build Validation:
     ```bash
     npm --prefix apps/web run build
     ```

### 3.3 Flutter Mobile Application Job (`mobile-ci`)
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout repository.
  2. Setup Java 17 and Flutter SDK (channel `stable`).
  3. Cache Flutter pub dependencies.
  4. Resolve dependencies:
     ```bash
     cd apps/mobile && flutter pub get
     ```
  5. Dart Formatting Check:
     ```bash
     dart format --output=none --set-exit-if-changed apps/mobile/lib apps/mobile/test
     ```
  6. Static Code Analysis:
     ```bash
     cd apps/mobile && flutter analyze --fatal-infos --fatal-warnings
     ```
  7. Mobile Unit & Widget Tests:
     ```bash
     cd apps/mobile && flutter test --coverage
     ```

### 3.4 Repository Security & Governance Job (`repo-security-ci`)
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. **Secret Scanning**: Run `gitleaks` across the commit history to detect accidentally exposed credentials, private keys, or API tokens.
  2. **Dependency Vulnerability Scanning**: Run `pip-audit` for Python and `npm audit --audit-level=high` for Node.js.
  3. **Docker Compose Validation**:
     ```bash
     docker compose config --quiet
     ```
  4. **Documentation Numbering & Integrity Check**: Run verification script checking that docs `00` through `28` and `MILESTONE_3_MANIFEST.md` exist and contain no broken relative markdown links.

---

## 4. Release & Deployment Gates

Continuous Delivery (CD) to campus servers follows a strict manual gating procedure:
1. All CI jobs on `main` must be green.
2. A formal release tag (e.g., `v1.0.0-pilot`) is created and digitally signed by an authorized maintainer.
3. Release candidate container images are built and pushed to the local university private registry.
4. An authorized systems administrator initiates deployment onto the campus server using the offline-capable deployment script.
