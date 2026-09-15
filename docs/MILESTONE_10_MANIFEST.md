# Digital Student Attendance System
## Milestone 10 Manifest — Dynamic QR & Cryptographic Presence Tokens

**Milestone:** 10 (Dynamic QR & Cryptographic Presence Tokens)  
**Git Branch:** `feature/task-008-dynamic-qr-presence-tokens`  
**Status:** Completed & Validated  
**Date:** September 2026  

---

## 1. File Inventory

| Path | Category | Description |
|---|---|---|
| `backend/app/core/config.py` | Configuration | Added typed `ATTENDANCE_QR_*` settings and cross-field cryptographic separation (`ATTENDANCE_QR_SIGNING_KEY != AUTH_SIGNING_KEY`) |
| `backend/app/attendance/tokens.py` | Cryptographic Engine | `PresenceTokenEngine` with deterministic rotation slots, authoritative expiration, HMAC-SHA256 signing, and strict verification |
| `backend/app/attendance/schemas.py` | Pydantic Schemas | `QrTokenResponse`, `QrCheckInRequest` (INV-01: no student_id in body), and `QrCheckInResponse` |
| `backend/app/attendance/service.py` | Domain Service | Implemented `generate_checkpoint_qr_token` and `verify_qr_checkin` integrating with M9 `record_verified_checkpoint_credit` |
| `backend/app/attendance/router.py` | API Router | Mounted `GET /checkpoints/{checkpoint_id}/qr-token` and `POST /qr/check-in` with RBAC and occurrence authority enforcement |
| `backend/tests/test_qr_tokens.py` | Unit Test Suite | 9 pure unit tests verifying claims, rotation slots, zero student PII, expiration, tampering rejection, and key isolation |
| `backend/tests/test_qr_service.py` | Integration Test Suite | 4 integration tests verifying shared classroom token, multi-student scans, idempotency, expired token rejection, and closed checkpoint handling |
| `backend/tests/test_qr_rbac.py` | RBAC Test Suite | 2 end-to-end API tests verifying lecturer authorization, unassigned lecturer 403, student check-in, repeat scans, and tampering rejection |
| `apps/web/src/components/LecturerQrDisplay.tsx` | Web Component | Projector-ready dynamic QR display with live rotation countdown, checkpoint status badge, and automatic re-fetch |
| `apps/mobile/lib/services/qr_checkin_service.dart` | Mobile Service | HTTP client service submitting dynamic QR tokens to the attendance backend |
| `apps/mobile/lib/screens/student_qr_scanner_screen.dart` | Mobile UI | Viewfinder and scanner screen with status feedback, manual entry fallback, and error handling |
| `apps/mobile/test/qr_checkin_service_test.dart` | Mobile Unit Tests | Unit tests verifying response deserialization and exception formatting |
| `apps/mobile/test/qr_scanner_screen_test.dart` | Mobile Widget Tests | Widget test verifying scanner UI rendering |
| `docs/41_MILESTONE_10_DYNAMIC_QR_PRESENCE_TOKENS.md` | Documentation | Architectural specification for dynamic QR presence verification |
| `docs/42_NEXT_IMPLEMENTATION_TASK.md` | Handoff Document | Boundary and entry specification for Milestone 11 |
| `scripts/check_docs.py` | Verification Script | Updated to validate docs 41, 42, and Milestone 10 manifest |

---

## 2. Invariant Audit

1. **Client Cannot Mark Itself Present (INV-01)**: Enforced. The mobile client sends scanned token evidence to `POST /api/v1/attendance/qr/check-in`. The server evaluates the token, verifies active session and checkpoint window, verifies frozen roster enrollment, and awards checkpoint credit. The client payload contains zero student identity fields.
2. **Attendance Depends on Server/Domain Validation (INV-02)**: Enforced. Checkpoint credit and status calculation execute exclusively in the core attendance engine (`AttendanceService.record_verified_checkpoint_credit`).
3. **Student Device Clock Is NOT Authoritative (INV-03)**: Enforced. Token rotation slot computation and expiration verification rely strictly on the university server's UTC clock. Device clock alterations cannot bypass token validity.
4. **Expired Dynamic QR/Tokens Cannot Grant Attendance (INV-04)**: Enforced. Dynamic tokens expire at the rotation slot boundary (30 seconds) or when the checkpoint window closes. Expired tokens are rejected with `QR_TOKEN_EXPIRED`.
5. **No Duplicate Checkpoint Credit (INV-05)**: Enforced. If an enrolled student scans a token for an already-credited checkpoint, the server returns an idempotent success response with `already_credited: true` without duplicating records or double-crediting.
6. **Classroom Shared Token Model**: Enforced. Multiple students in the same class scan the identical rotating visual classroom QR token; each distinct student receives credit against their own roster record.
7. **Zero Student PII**: Enforced. Displayed projector tokens contain only university, session, checkpoint, and slot metadata. No student IDs, names, or device information exist in the token payload.
8. **Cryptographic Key Separation**: Enforced. Dynamic QR tokens are signed with `ATTENDANCE_QR_SIGNING_KEY`, which is validated at startup to be distinct from `AUTH_SIGNING_KEY`. Tokens signed with the authentication key are rejected.
9. **Zero Database Schema Drift**: Enforced. Reuses existing `AttendanceEvidence` (from migration 008) with `source_mode="ONLINE_DYNAMIC_QR"` and `SHA-256(token)` in `evidence_metadata`. Zero database migrations required.
