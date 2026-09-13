# Digital Student Attendance System
## Release and Versioning Strategy

**Document Version:** 1.0  
**Status:** Approved Operational Strategy  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Versioning Standard

The Digital Student Attendance System strictly adheres to **Semantic Versioning 2.0.0** (`MAJOR.MINOR.PATCH`):
- **MAJOR**: Incompatible API breaking changes, major institutional schema overhauls, or breaking mobile protocol migrations.
- **MINOR**: Backward-compatible new functionality (e.g., adding Bluetooth presence verification, adding new report types).
- **PATCH**: Backward-compatible bug fixes, security patches, and minor performance improvements.

---

## 2. Release Progression Plan

The project follows a structured progression through development milestones to the first production campus deployment:

| Version | Milestone Scope | Target Gate |
| :--- | :--- | :--- |
| `0.1.0` | **Bootstrap Baseline** | Monorepo scaffolding, health checks, CI pipelines, Docker Compose. (Milestone 3) |
| `0.2.0` | **Identity & Security** | User authentication, Argon2id, JWT tokens, RBAC permissions. (Milestone 4 - Phase 2) |
| `0.3.0` | **Academic Core** | Universities, faculties, departments, semesters, sections, student/lecturer rosters. |
| `0.4.0` | **Scheduling** | Rooms, recurring timetable rules, concrete class occurrences. |
| `0.5.0` | **Attendance Engine** | Three-checkpoint session lifecycle, attendance policies, final record resolution. |
| `0.6.0` | **Dynamic Presence** | Dynamic rotating QR tokens, Flutter mobile check-in, cryptographic device binding. |
| `0.7.0` | **Resilience & Fallback** | BLE presence evidence, staff physical card scanning, offline permits, sync outbox. |
| `0.8.0` | **Governance & Analytics** | Immutable audit logs, corrections workflow, debarment warnings, PDF/Excel exports. |
| `0.9.0-rc.1` | **Pilot Release** | End-to-end integration, performance tuning, security hardening, pilot faculty deployment. |
| `1.0.0` | **Production University Release** | Full campus deployment across all faculties, automated campus backups, validated SLA. |

---

## 3. Pre-Release & Development Tagging

- **Development Builds**: Automatically tagged in CI as `<version>-dev.<commit-sha>` (e.g., `0.2.0-dev.7b1a4f2`).
- **Release Candidates**: Formally tagged as `<version>-rc.<number>` (e.g., `0.9.0-rc.1`) during pilot staging.
- **Hotfix Builds**: Versioned as `<version>.<patch>` (e.g., `1.0.1`) created directly from verified fixes to `main`.

---

## 4. Git Tagging & Changelog Maintenance

### Tagging Procedure
Every formal release requires an annotated, cryptographically signed Git tag created on the `main` branch:
```bash
git tag -a v0.1.0 -m "Release v0.1.0: Milestone 3 Repository & Implementation Blueprint Baseline"
git push origin v0.1.0
```

### Changelog Format (`CHANGELOG.md`)
Releases are documented following the **Keep a Changelog** standard with sections:
- `Added`: New features and endpoints.
- `Changed`: Modifications to existing behavior.
- `Deprecated`: Features scheduled for removal.
- `Removed`: Removed capabilities.
- `Fixed`: Bug and defect fixes.
- `Security`: Vulnerability resolutions and hardening.

---

## 5. Database Migration Compatibility & Rollback Strategy

In a production university environment, downtime and data loss are intolerable.

### Backward-Compatible Migration Rule
1. **Expand and Contract Pattern**:
   - New database columns must be added as `NULLABLE` or provide safe defaults in Phase A.
   - Application code is deployed in Phase B to write to both new and legacy fields.
   - Obsolete columns are deprecated and safely dropped in Phase C.
2. **Reversible Migrations**:
   - Every Alembic migration must contain a verified `downgrade()` script.
   - Before executing migrations on the campus production server, an automated snapshot of the PostgreSQL volume is taken by the backup agent.

### Rollback Protocol
If a deployment exhibits critical failures during post-deployment smoke tests:
1. Revert container image tags to the previous stable release version.
2. Execute Alembic downgrade if database migrations were applied and are safely reversible:
   ```bash
   alembic downgrade -1
   ```
3. If database changes are irreversible or corrupted, restore the pre-deployment database snapshot:
   ```bash
   bash infra/backup/restore.sh --snapshot pre-deploy-v1.0.0
   ```
4. Perform post-rollback health checks (`/health/live`, `/health/ready`) to confirm service restoration.
