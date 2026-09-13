# Digital Student Attendance System
## Milestone 6 Manifest — Academic Structure, Hierarchy & Master Data

**Milestone:** 6 (Academic Structure, Hierarchy & Master Data)  
**Git Branch:** `feature/task-004-academic-structure`  
**Base Commit:** `28bd37b`  
**Status:** Completed & Validated  
**Date:** September 2026  

---

## 1. File Inventory & SHA-256 Hashes

| Path | Category | SHA-256 Digest |
|---|---|---|
| `backend/app/core/constants.py` | Configuration & Enums | `a869529556a26dbbf1901538bc10a3859063c101c9b8756526537bb434f8e133` |
| `backend/app/models/academic_unit.py` | Data Model | `33b0b0eebcba514333955db03e466daaa38829b4e035cdb29b74a5505f0c7a2b` |
| `backend/app/models/academic_year.py` | Data Model | `fdef9897af5601059b65d0529d6d164a1ef238e28889e137f5e32618f7f2dd60` |
| `backend/app/models/semester.py` | Data Model | `ffa7330fa7270eec83bfec203aa8ee218a7292725cbf678d4ee1e40976330845` |
| `backend/app/models/__init__.py` | Model Exports | `0e15cefe0e23d8f137bbcd1d51675644ac70230ba8deafd3ed4e56b09e548de2` |
| `backend/migrations/versions/005_academic_units_and_calendar.py` | Database Migration | `d0ec63a03f0f21b44bcb0dfbdffddedc5366cc9ae222a54ab278b6aa797be8a1` |
| `backend/app/academic/__init__.py` | Package Init | `11feee12dfe0368160d77e164d3bf54d721478ee24aa02747b22c99e1c25cf48` |
| `backend/app/academic/schemas.py` | Pydantic Schemas | `42a8e60cf6f3d201002745605a5990cecd85c88c9b7cf4c82acb7e67164a9f11` |
| `backend/app/academic/service.py` | Domain Service | `c4f75d099d1bbcef0b3fd61482dd0879ab7ca277d9c52569af9ce67525c119d7` |
| `backend/app/academic/router.py` | API Router | `8a7bfd1328203befb721ce16fa2fee08b5e029ffe8f873aba3876f39d93a4f95` |
| `backend/app/calendar/__init__.py` | Package Init | `9032c78080dbc9d6c583f558f2c1d7a49079daec5d4c2269110399d9aae98e30` |
| `backend/app/calendar/schemas.py` | Pydantic Schemas | `6a1218a01f13295d9b60c16e40a3112e9a8a2372efb7953ebfc5a965fa808534` |
| `backend/app/calendar/service.py` | Domain Service | `f37cbaae450edd9aca708ba945c4f3c1426ec4880dacf14ec5bf659d1f82a05f` |
| `backend/app/calendar/router.py` | API Router | `48ac47b849361fe7dcfee1eb9d922dc5a4d62c0790bdf9161b67a489ab41f615` |
| `backend/app/api/v1/router.py` | API Root Router | `a3aad4b901105b3513b8a1cfcc8e592bd4e32a798c0f09ea5b003f605fb58f7d` |
| `backend/app/rbac/seeding.py` | RBAC Seeder | `29b0155791fdee384cb9ea14aeddecd72ec894c234191bccb5a070c1cd319178` |
| `backend/app/rbac/service.py` | RBAC Service | `83c2883345cefb957bebe309906651e84407c49eccfebfd2ca4a66dc053209d2` |
| `backend/app/rbac/dependencies.py` | RBAC Dependencies | `1c4e3b042a113f1ecdfd77cec37ebab0d4f63eca6f9af528acc2f622d827686b` |
| `backend/tests/test_academic_units.py` | Test Suite | `b0afd7a976577bf2c8ed16632890a1b1b3c30924d249143f47576703cf6128ff` |
| `backend/tests/test_academic_calendar.py` | Test Suite | `a817cb7bd85fc64454f34fcf6841287a1852df005229df54fa802409c671d1e1` |
| `backend/tests/test_academic_rbac.py` | Test Suite | `ec6f76d09e4e6508c91e47753fa1d05746f923502502a770626b71d4c5d9a389` |
| `backend/tests/test_rbac.py` | Test Suite Update | `a5d9e1db0166ef4b436ae6af01117175f912ea0cfecd7fe5a1603a8a7a800ed7` |
| `docs/33_MILESTONE_6_ACADEMIC_STRUCTURE_MASTER_DATA.md` | Specification Document | `46fc942add93b45a570110a49beb3316a562ca8b1d4be7395eac88e7fdc7daf4` |

---

## 2. Invariant Audit

All invariants established in `AGENTS.md` and specification documents `00`–`15` have been audited:

1. **Client Cannot Mark Itself Present (INV-01)**: Preserved. No attendance endpoints introduced.
2. **Attendance Depends on Server/Domain Validation (INV-02)**: Preserved. Domain structure created for future linkage.
3. **Student Device Clock Is NOT Authoritative (INV-03)**: Enforced. Academic calendar date windows and active periods are validated using server UTC dates.
4. **Expired Dynamic QR/Tokens Cannot Grant Attendance (INV-04)**: Preserved. Deferred to Milestone 8+.
5. **No Duplicate Checkpoint Credit (INV-05)**: Preserved. Deferred to Milestone 8+.
6. **Corrections Cannot Erase History (INV-06)**: Preserved. Deferred to Milestone 8+.
7. **Offline Events Remain Identifiable (INV-07)**: Preserved. Deferred to Milestone 9+.
8. **Manual Attendance Overrides Remain Identifiable (INV-08)**: Preserved. Deferred to Milestone 8+.

---

## 3. Verification Summary

```text
Backend Tests:             100 passed (100%)
Ruff Linter:               Passed (0 warnings)
Ruff Formatter:            Passed (89 files formatted)
Mypy Strict Typecheck:     Passed (89 files checked, 0 errors)
Docker Alembic Check:      Passed (No schema drift against PostgreSQL 16)
Docker Migration Downgrade:Passed (005 -> 004 reversible)
Docker Migration Upgrade:  Passed (004 -> 005 clean)
Next.js Lint & Typecheck:  Passed (0 warnings)
Next.js Turbopack Build:   Passed (Optimized production build)
Flutter Analyze:           Passed (0 issues)
Flutter Tests:             3 passed (100%)
Secret Scan:               Passed (Zero exposed secrets)
```
