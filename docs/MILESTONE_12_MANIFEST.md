# Milestone 12 Manifest: Offline Attendance, Signed Offline Authority & Reconciliation

**Status:** COMPLETE  
**Branch:** `feature/task-010-offline-attendance-reconciliation`  
**Quality Gate:** PASS  

---

## 1. Components Implemented

### Cryptography & Domain Services
- `backend/app/attendance/offline_crypto.py`: Ed25519 asymmetric operations, permit token engine, dynamic rotating challenge generation, monotonic anchor math, and event hash-chain verification.
- `backend/app/attendance/offline_service.py`: Permit issuance, host event ingestion, student claim processing, and out-of-order deterministic reconciliation pipeline.
- `backend/app/attendance/offline_schemas.py`: Pydantic V2 request and response contracts.
- `backend/app/attendance/offline_router.py`: REST API routes mounted under `/api/v1/attendance/offline`.
- `backend/app/attendance/tasks.py`: Asynchronous Celery reconciliation worker task.

### Database & Migration
- `backend/app/models/offline_attendance.py`: SQLAlchemy models for `OfflineAttendancePermit`, `OfflineHostSession`, `OfflineHostEvent`, `OfflineAttendanceClaim`, `SyncInboxEntry`, and `OfflineSyncConflict`.
- `backend/migrations/versions/009_offline_attendance_reconciliation.py`: Versioned Alembic migration with full `upgrade()` and `downgrade()`.

### Mobile Client (Flutter)
- `apps/mobile/lib/core/offline/monotonic_clock.dart`: Monotonic uptime clock anchor abstraction.
- `apps/mobile/lib/core/offline/offline_storage.dart`: Local offline outbox models and deduplication cache.
- `apps/mobile/lib/screens/lecturer_offline_host_screen.dart`: Lecturer hosting screen with rotating QR display and event hash chain recording.
- `apps/mobile/lib/screens/student_qr_scanner_screen.dart`: Offline QR challenge detection and outbox queueing with pending sync state.
- `apps/mobile/test/offline_attendance_test.dart`: Unit tests for mobile clock anchor and outbox storage.

### Testing & Verification
- `backend/tests/test_offline_crypto.py`: 8 unit tests for Ed25519 and monotonic math.
- `backend/tests/test_offline_service.py`: 3 service integration tests with hash chain tamper detection.
- `backend/tests/test_offline_reconciliation.py`: End-to-end integration test verifying student-before-host out-of-order auto-reconciliation and attendance credit.
- `backend/tests/test_offline_rbac.py`: 4 RBAC security and permission tests.
- CI Workflow: Added offline test files to Shard 4 matrix.

---

## 2. Invariants Verification

- **INV-01**: Verified. Client submissions write to `offline_attendance_claims` with state `PENDING_HOST_EVENTS` or `VERIFIED` strictly through `AttendanceService.record_verified_checkpoint_credit`.
- **INV-03**: Verified. Monotonic uptime anchor prevents device clock cheating; server clock is sole authority.
- **INV-04**: Verified. Expired dynamic challenges outside tolerance window rejected.
- **INV-05**: Verified. Unique constraints prevent duplicate checkpoint credit.
- **INV-07**: Verified. Reconciled records carry `source_mode="OFFLINE_SYNC"` and create immutable `AttendanceRevision` entries.
