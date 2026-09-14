# Digital Student Attendance System
## Milestone 9 Manifest — Attendance Core Engine & Policy

**Milestone:** 9 (Attendance Core Engine & Policy)  
**Git Branch:** `feature/task-007-attendance-core`  
**Status:** Completed & Validated  
**Date:** September 2026  

---

## 1. File Inventory & SHA-256 Hashes

| Path | Category | SHA-256 Digest | Description |
|---|---|---|---|
| `backend/app/core/constants.py` | Core Constants | `83b8cbf837150adc439ec6eac7b2945de53855a3ead574a511a7ee252e1642a0` | Added M9 permissions (`attendance_policies.*`, `attendance_sessions.*`, `attendance_records.*`, etc.) and attendance enums |
| `backend/app/models/attendance_policy.py` | Data Model | `adb69208bf544af23e00979880c361e209044e6479a8fe4aaeb5f73c0074786c` | Hierarchical attendance policy model with multi-tier scope support |
| `backend/app/models/attendance_session.py` | Data Model | `e6400011bccff96bc3f702a43c21fcfbb4dc21ebe654adc9309a14d268feee2e` | Attendance session lifecycle model anchored to class occurrence |
| `backend/app/models/attendance_checkpoint.py` | Data Model | `c28ae27bfec24fc76dc9f2cf820baf934bf8de83d7cfc14b41ed710f1ed5411d` | 3-checkpoint discrete model (`START`, `MIDDLE`, `END`) with UTC windows |
| `backend/app/models/attendance_evidence.py` | Data Model | `7de09fc97185aeb600a5da4e976ff93becad988969ca17f893bcbed80ff8d930` | Presence evidence records with session-checkpoint-student uniqueness |
| `backend/app/models/attendance_record.py` | Data Model | `b0ca8fa554b22e41465f9cd30ba0b65ee2e9e2e596a6c25b20db9c93f85d093d` | Student session roster record snapshot with score and status |
| `backend/app/models/attendance_revision.py` | Data Model | `68005af3e1c23df7502c9783810d79fc07bbcc92fa279b7960e03793def690b2` | Append-only audit revision ledger for manual overrides and corrections |
| `backend/app/models/__init__.py` | Model Exports | `2386a167ec0b69baedf23fd7f8abc5c0cbdeeb52db37c2d57f7662785f9b2991` | Exported M9 attendance entities |
| `backend/migrations/versions/008_attendance_core.py` | Database Migration | `7444c84936ef6ef7533016ef13406cc9fc0aa87d08e91858c01bcc2df9ba2b66` | Reversible Alembic migration 008 with foreign keys, indexes, and checks |
| `backend/app/rbac/seeding.py` | RBAC Seeder | `29d413651dd89f2940883b80cd06ccafc15fc4fef8eeae2abf36f2e403af8a0a` | Seeded 9 M9 permissions into canonical system roles |
| `backend/app/attendance/__init__.py` | Package Init | `9a6fc668ff0a4920a7928dbb36c2064c91e9f5fd63df68b4497c697319d760ed` | Attendance module initialization |
| `backend/app/attendance/schemas.py` | Pydantic Schemas | `33b32a4414561a8e510767d8aa2429c4f148b5fa0970b0fd2f0483c6700840c3` | Pydantic v2 request/response validation schemas for M9 |
| `backend/app/attendance/service.py` | Domain Service | `2ce68667fd44e0e279effa08acd091b368d0cc93097ff1d51eaf659c84cea8c6` | Core business logic: policy hierarchy, sessions, checkpoints, evaluation, overrides |
| `backend/app/attendance/router.py` | API Router | `bcf48c1fc5b9659ed3c576a4f8b00ba3b5f66aa86532924733565888f129563e` | REST endpoints for `/api/v1/attendance` and student history self-service |
| `backend/app/api/v1/router.py` | API Router Mount | `426fcf9ae57311e519971e43ddde880ab468fdcfa64602516a446cda48de8496` | Mounted attendance router onto `/api/v1` |
| `backend/tests/test_attendance_policy.py` | Test Suite | `86150c2c1e76c71c786afa63a20a2de1c01bd5a18076fca14eed633e6a66fd12` | Policy hierarchy resolution and threshold validation tests |
| `backend/tests/test_attendance_sessions.py` | Test Suite | `72db04103889cfabaab773e260c31a1d4a95645c3330a98fae945ee664b49e16` | Session lifecycle state transitions and active roster snapshot tests |
| `backend/tests/test_attendance_checkpoints.py` | Test Suite | `4bcd51f76c76d9f1e377e52a7a8ddb0869b4df40fafd893ba0e325ca36f5bc68` | Checkpoint window expiration and duplicate credit prevention tests |
| `backend/tests/test_attendance_evaluation.py` | Test Suite | `8a614d6b11cb62e78794415470bbe70411310b224d79482b07923df39c197471` | Combinatorial 8-pattern evaluation and status calculation tests |
| `backend/tests/test_attendance_overrides_and_audit.py` | Test Suite | `43bf2ff648b4b72a6569c5065d8c9be4f831effe29279750f9bb2d94bb21c129` | Manual override justification, append-only revisions, self-views, audit |
| `backend/tests/test_attendance_rbac.py` | Test Suite | `f72ad55012cb0888d35fe0b95da147911a232886b5461c09401c9a72b051609c` | Scoped RBAC, student isolation, unassigned lecturer rejection tests |
| `backend/tests/test_rbac.py` | Test Suite Update | `2e8fa5f90152d14a198c9bb484ab817dd4858452bb938658a8fa50ae439690a1` | Updated RBAC test for 58 total system permissions |
| `docs/23_DATABASE_MIGRATION_PLAN.md` | Migration Plan | `154a2e8ee8992ceae504acdbd4fbd31cb3da6ed261f8bf5dbd767c81f50e6c20` | Updated with migration 008 details, status, and rollback proof |
| `docs/39_MILESTONE_9_ATTENDANCE_CORE.md` | Specification Document | `2fe5ea8f987712912e3bae2c67168a23711bd437c6e184aef0172c12ec58c527` | Milestone 9 architecture, implementation, and invariant proof |
| `docs/40_NEXT_IMPLEMENTATION_TASK.md` | Handoff Specification | `e4d97365584b1ccd947d79bbd8a4ecd0c0722cf6ae44f0764b96de0d0f3fb6a9` | Milestone 10 entry point task document |
| `scripts/check_docs.py` | Verification Script | `c42549d92f274492e07d2fa971d416f7d376b930c8e522e3641a04958036983a` | Updated documentation validation script for docs 39, 40, M9 manifest |

---

## 2. Invariant Audit

All invariants established in `AGENTS.md` and specification documents `00`–`15` have been audited:

1. **Client Cannot Mark Itself Present (INV-01)**: Enforced. Evidence submitted to server; attendance engine evaluates windows, validity, and thresholds before awarding status.
2. **Attendance Depends on Server/Domain Validation (INV-02)**: Enforced. Status transitions (`PRESENT`, `LATE`, `ABSENT`, `EXCUSED`, `LEAVE`) execute exclusively in domain services.
3. **Student Device Clock Is NOT Authoritative (INV-03)**: Enforced. University server UTC clock governs checkpoint windows, session transitions, and evidence verification timestamps.
4. **Expired Dynamic QR/Tokens Cannot Grant Attendance (INV-04)**: Preserved. Cryptographic token scheme deferred to Milestone 10. Checkpoint window expiration rejection is strictly enforced in M9.
5. **No Duplicate Checkpoint Credit (INV-05)**: Enforced. Unique database constraint `(attendance_session_id, attendance_checkpoint_id, student_id)` prevents double counting.
6. **Corrections Cannot Erase History (INV-06)**: Enforced. `attendance_revisions` ledger is append-only; overrides record prior and new status with monotonic revision increments.
7. **Offline Events Remain Identifiable (INV-07)**: Preserved. Schema supports `OFFLINE_CAPTURED`; offline synchronization protocols deferred to Milestone 12.
8. **Manual Attendance Overrides Remain Identifiable (INV-08)**: Enforced. Mandatory non-empty reason and actor user ID recorded on every manual override.
