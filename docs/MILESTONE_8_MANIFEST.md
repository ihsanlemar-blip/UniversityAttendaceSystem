# Digital Student Attendance System
## Milestone 8 Manifest — Facilities, Timetable & Class Occurrences

**Milestone:** 8 (Facilities, Timetable & Class Occurrences)  
**Git Branch:** `feature/task-006-facilities-timetable-occurrences`  
**Status:** Completed & Validated  
**Date:** September 2026  

---

## 1. File Inventory & SHA-256 Hashes

| Path | Category | SHA-256 Digest | Description |
|---|---|---|---|
| `backend/app/core/constants.py` | Core Constants | `0e5e0913456d4ed8fbaf9abd1fb9cb9df2f26b097bddbeb94f8cdc7e53462d3c` | Added M8 permissions (`buildings.*`, `rooms.*`, `timetables.*`, `class_occurrences.*`) and status enums |
| `backend/app/core/exceptions.py` | Exceptions | `5388a3d6a91649a48f632c80fd5db7b1fbad033a335c5918aac3121569f1ad67` | Added optional custom error code parameter to `ConflictException` |
| `backend/app/models/building.py` | Data Model | `3d8c3093c6a38f596ea81acd831c4b75bac51f69678494ad78cb515a47a9ca87` | Campus physical structure model with institutional code uniqueness |
| `backend/app/models/room.py` | Data Model | `95e836abde7c957d776e589415c47a81fc687bdbee34dd80ca0181f38638f789` | Room facility model with capacity checks and building uniqueness |
| `backend/app/models/timetable.py` | Data Model | `db6a8cf7d7b7a3bc379741a72d8eb97c87e909e538a5d43ddb34c2c1127b446c` | Weekly recurring schedule rules with range checks and foreign keys |
| `backend/app/models/class_occurrence.py` | Data Model | `1f9bb3e9123732f8d28fce8f22b9b94f482b108cec322ccb603844e474f19e07` | Concrete calendar meeting occurrences with UTC timestamps |
| `backend/app/models/__init__.py` | Model Exports | `1ace74582dc3579945fa116ef919cfcd0f71b82a4a048901660a2236c4893bb2` | Exported `Building`, `Room`, `Timetable`, `ClassOccurrence` models |
| `backend/app/rbac/seeding.py` | RBAC Seeder | `b9a36abea0add08f66a89aa7e9cd461ecd5aad7b9e05ae6e26a11bb6e0d1155f` | Seeded M8 permissions into canonical system roles |
| `backend/migrations/versions/007_timetable_and_class_occurrences.py` | Database Migration | `0116d3b378bf7f34143ef0d33705074877b56f59d42a1d3bfef126e6356a424f` | Reversible Alembic migration 007 with indexes and constraints |
| `backend/app/facilities/__init__.py` | Package Init | `65b44535165c4a83aded7744ef416dd5aa099ca95574f8c8a88cbc2b45f1982b` | Facilities module initialization |
| `backend/app/facilities/schemas.py` | Pydantic Schemas | `5c59122e2a929ef68fd50f9c1b82301fc23db97601fd1fe621b5d3b70c39a77d` | Building and Room request/response data contracts |
| `backend/app/facilities/service.py` | Domain Service | `48f4ee4f1932cb47e98f73f712314c2b5d2bc389bb72b7822ec4b50108f1d042` | Facilities business logic (building and room lifecycle) |
| `backend/app/facilities/router.py` | API Router | `46a2b7b2236a441655b8a488e692b0c4cb64a1a8a10d35e177999d25e64d42f7` | REST endpoints for `/api/v1/buildings` and `/api/v1/rooms` |
| `backend/app/scheduling/__init__.py` | Package Init | `86a64e61f76147fa8854d61ebafaaa012c62220968fc82c34a4f7ebb068144ca` | Scheduling module initialization |
| `backend/app/scheduling/schemas.py` | Pydantic Schemas | `08cd17ca3a8119360a8f8f055ff0814bb03692c77aef6538be2f437d2d64d7d5` | Timetable and ClassOccurrence request/response schemas |
| `backend/app/scheduling/service.py` | Domain Service | `e9b956edd0c6559e2984e5cb50c36b109940506ea88550d047636689a97f5668` | Scheduling service: conflict engine, occurrence generator, cancel, reschedule, self-views |
| `backend/app/scheduling/router.py` | API Router | `d27e1990c18a37f98481658ab7b67d252317f230052204e1595b4176571c9339` | REST endpoints for `/api/v1/timetables` and `/api/v1/class-occurrences` |
| `backend/app/api/v1/router.py` | API Router Mount | `4276764c5fbe808ff0508521dbd0fd17a0ba9ca5b4f3592ad71524d5725589e5` | Mounted facilities and scheduling routers onto `/api/v1` |
| `backend/tests/test_facilities.py` | Test Suite | `054644c3599c416158a07fe1e2c0b2eb46574c98d4d0b8b54386347ad3523576` | Unit & integration tests for buildings, rooms, and tenant isolation |
| `backend/tests/test_timetables.py` | Test Suite | `255eee2e64b80940aaf9fa944b270e9d86db862f119687380941eb82cffa584b` | Unit & integration tests for timetables, conflict engine, boundaries |
| `backend/tests/test_occurrences.py` | Test Suite | `64c8302e6447740323e2f9067983efc259390fa84698efa09603db9ad387ae33` | Unit & integration tests for occurrence generation, cancel, reschedule |
| `backend/tests/test_scheduling_rbac.py` | Test Suite | `1d37d0a8d365fd4454a52f5cb4fc7e3a6dfd5ea7524d92b07ff2612fc9cf06dd` | Unit & integration tests for scoped RBAC and personal schedule self-views |
| `backend/tests/test_rbac.py` | Test Suite Update | `9cc713e3e8a928b95437e1267b74c19496e71299d753d8e93e32652f34ed3d21` | Updated RBAC test for total permission count |
| `docs/37_MILESTONE_8_FACILITIES_TIMETABLE_OCCURRENCES.md` | Specification Document | `c73d1289be052075525df10e76aa55c0e5252589a1e589e7b7434be7422a96df` | Milestone 8 architecture, implementation, and invariant proof |
| `docs/38_NEXT_IMPLEMENTATION_TASK.md` | Handoff Specification | `902500435118e302266d9a8d4f70444e7903f7e5c4b671675614ea1f571cc3c4` | Milestone 9 entry point task document |
| `docs/23_DATABASE_MIGRATION_PLAN.md` | Migration Plan | `ca95cefc0b730910456a9c627664df4595e3cf7cdbd40d7546fef8f70457582b` | Updated with migration 007 details and status |
| `scripts/check_docs.py` | Verification Script | `ae0c4cddb5cf32eef2100f5d4bbbddba40fc0722c32a9120a35242f44000aa05` | Updated documentation validation script for docs 37, 38, M8 manifest |

---

## 2. Invariant Audit

All invariants established in `AGENTS.md` and specification documents `00`–`15` have been audited:

1. **Client Cannot Mark Itself Present (INV-01)**: Preserved. No attendance session or check-in endpoints introduced.
2. **Attendance Depends on Server/Domain Validation (INV-02)**: Preserved. Concrete class occurrences establish authoritative server-side anchors for future attendance sessions in Milestone 9.
3. **Student Device Clock Is NOT Authoritative (INV-03)**: Enforced. University official timezone (`ZoneInfo(university.timezone)`) converted into authoritative server UTC timestamps (`scheduled_start_utc`, `scheduled_end_utc`).
4. **Expired Dynamic QR/Tokens Cannot Grant Attendance (INV-04)**: Preserved. Deferred to Milestone 10+.
5. **No Duplicate Checkpoint Credit (INV-05)**: Preserved. Deferred to Milestone 9+.
6. **Corrections Cannot Erase History (INV-06)**: Enforced. Class occurrence cancellation preserves database rows and requires recorded justification; rescheduling preserves audit history with bi-directional links.
7. **Offline Events Remain Identifiable (INV-07)**: Preserved. Deferred to Milestone 12+.
8. **Manual Attendance Overrides Remain Identifiable (INV-08)**: Preserved. Deferred to Milestone 9+.
