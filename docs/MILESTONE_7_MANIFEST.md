# Digital Student Attendance System
## Milestone 7 Manifest — Master Curriculum, People Profiles, Rosters & Course Offerings

**Milestone:** 7 (Master Curriculum, People Profiles, Rosters & Course Offerings)  
**Git Branch:** `feature/task-005-curriculum-rosters-offerings`  
**Base Commit:** `9390234`  
**Status:** Completed & Validated  
**Date:** September 2026  

---

## 1. File Inventory & SHA-256 Hashes

| Path | Category | SHA-256 Digest |
|---|---|---|
| `backend/app/core/constants.py` | Configuration & Enums | `8b32cbf5ace8f199877c363154dc6cbba8e7f9302836164f2f15caaf031bd384` |
| `backend/app/models/course.py` | Data Model | `18e89626d5cb3bbf69fda6c63a5f34e681d88b3bedeb81894c54ee6bd2fd75c0` |
| `backend/app/models/section.py` | Data Model | `db792d325771857fc8bd54a1e777e1e4887e4501d4aa163182e93536ae210400` |
| `backend/app/models/student.py` | Data Model | `416526ee305f527e9e0fbc40164d797ecc7d89ac1d374d9a21fda1552079e8c3` |
| `backend/app/models/lecturer.py` | Data Model | `70a2b7f749eafc89ece421b5c2b8b509c9a4ad44dee3b425e747eeda1cee2f24` |
| `backend/app/models/course_offering.py` | Data Model | `4d8eedfc7b63e9f5f097166fcc8b2cd94edbf674b1cfe58da102730b5e13c660` |
| `backend/app/models/lecturer_assignment.py` | Data Model | `f565648db7554001e8bec2edc9a02e548761a58171263f9418b54e539769091a` |
| `backend/app/models/enrollment.py` | Data Model | `173e7a597328ea860207596778560cfd8a2ca5a2d9937f569a521313b61ace1d` |
| `backend/app/models/__init__.py` | Model Exports | `abecab35fa76144a9c792006f9cea8035b5761af020ce37548208896cf130bfa` |
| `backend/migrations/versions/006_curriculum_and_rosters.py` | Database Migration | `2f20ad9e4012d46bb32bd231ec6240befeb09117f2bec5143a702a2f1fdd03f3` |
| `backend/app/curriculum/__init__.py` | Package Init | `d7e06de0214228005f7ae36455b1ee83d3335ef840900e63a9dcc7b21bebe33d` |
| `backend/app/curriculum/schemas.py` | Pydantic Schemas | `8d671916177cb85151259ced84726f40a322a06a815841ead63e5d7d04634736` |
| `backend/app/curriculum/service.py` | Domain Service | `5890aa46982651b5a26328ed1fe99fcf7b4e56e69d6d6d552a4ac98a74814727` |
| `backend/app/curriculum/router.py` | API Router | `f418b5a1fff07d4fd5cf4c29f3301747e82fbdfb615950d15a5abd956647b65b` |
| `backend/app/people/__init__.py` | Package Init | `9a4b2a1e85302609e25462c4170e478788140cefe96957a3a0bca0015a8ccce3` |
| `backend/app/people/schemas.py` | Pydantic Schemas | `cbfc0b249437993ccdea5cb861979eb752b9ca19f36635a4f3a961e94a710072` |
| `backend/app/people/service.py` | Domain Service | `dfee13a2613ca68b51ef9b7d64c958e75f3528eaef306aba525d72afe85a330b` |
| `backend/app/people/router.py` | API Router | `09639b4330dd976fa98cb88ce28b16b76cd9f7139a98e492a63670bc9f51208b` |
| `backend/app/offerings/__init__.py` | Package Init | `9fc73d971ef67e8d771379bcfb5523cd5f9279f50af92093a018d7a88bcae8fb` |
| `backend/app/offerings/schemas.py` | Pydantic Schemas | `9eb826e2b434e7d93846687e197e2c2760a2582e775d7ae3a9d5f6ca6e5ca49d` |
| `backend/app/offerings/service.py` | Domain Service | `c43112baf7d960e2c78e4a8f8a9e18a27bd4fd6816e4999acba592831dad8112` |
| `backend/app/offerings/router.py` | API Router | `522f264d28d2007f5f6e3c38cae74369f82e59a9628da465163ad4fb362d5a9d` |
| `backend/app/api/v1/router.py` | API Root Router | `5bb6e843e3f4ca67cb48794b134976a6d7856ce55984c29da67be7c0911d4246` |
| `backend/app/rbac/seeding.py` | RBAC Seeder | `27880388efc99cb3b2ddc32940bcc2a5f8349cf455173a159efcf6e4e5f0f2e4` |
| `backend/app/rbac/service.py` | RBAC Service | `cb1d0ec0a5b1c9d0413b818892e113ff660acc4cb3c10edd2ce71a15d3fc9a8f` |
| `backend/app/rbac/dependencies.py` | RBAC Dependencies | `34f7ca8f13248238e2b284d43937c0600263ff4d57b23b5d3673cc4fe155dae2` |
| `backend/tests/test_courses.py` | Test Suite | `23bc362df0b11a852de5e15c2b07c5648de31729488ab8c01c7e70b4bdde6242` |
| `backend/tests/test_sections.py` | Test Suite | `4438ce2a424556b2214829a7bfa43cf3708150f6d10f1217897e1c1c207b6e4d` |
| `backend/tests/test_people.py` | Test Suite | `1d358f30fe2c0d32c251c9813abee9c4349c613339630a0e11b6992ef64db3d4` |
| `backend/tests/test_offerings.py` | Test Suite | `31ad69ad902ce6531759e6a397cfc3c94e40393ec23d76c794b2088f463a6623` |
| `backend/tests/test_curriculum_rbac.py` | Test Suite | `99ba43a9590848b27cdc7caa3488df02e69cd076fba593e394104af57941752d` |
| `backend/tests/test_rbac.py` | Test Suite Update | `242d72932c6a3475bda253c841b385a83131428ef8af76cd507163c79a934b87` |
| `backend/tests/conftest.py` | Test Fixtures | `28059c4c80618f743cea52184f13a554f8ead957ecc3ea8c85690684e373053f` |
| `docs/35_MILESTONE_7_CURRICULUM_ROSTERS_OFFERINGS.md` | Specification Document | `f10685a5e03bf0f57c901ec07dd5acaf381e214deefa8a76fba0080788d20364` |

---

## 2. Invariant Audit

All invariants established in `AGENTS.md` and specification documents `00`–`15` have been audited:

1. **Client Cannot Mark Itself Present (INV-01)**: Preserved. No attendance endpoints introduced.
2. **Attendance Depends on Server/Domain Validation (INV-02)**: Preserved. Course offerings and enrollment rosters established for future attendance session anchoring.
3. **Student Device Clock Is NOT Authoritative (INV-03)**: Enforced. Enrollment timestamps (`enrolled_at`, `dropped_at`) and audit logs generated using server UTC authority.
4. **Expired Dynamic QR/Tokens Cannot Grant Attendance (INV-04)**: Preserved. Deferred to Milestone 10+.
5. **No Duplicate Checkpoint Credit (INV-05)**: Preserved. Deferred to Milestone 9+.
6. **Corrections Cannot Erase History (INV-06)**: Enforced. Enrollment dropping preserves historical presence with `status = DROPPED` and `dropped_at` timestamp.
7. **Offline Events Remain Identifiable (INV-07)**: Preserved. Deferred to Milestone 12+.
8. **Manual Attendance Overrides Remain Identifiable (INV-08)**: Preserved. Deferred to Milestone 9+.

---

## 3. Verification Summary

```text
Backend Test Suite:        121 passed (100%)
Ruff Linter:               All checks passed (0 errors)
Ruff Formatter:            114 files inspected, all formatted
MyPy Strict Typechecker:   Success: no issues found in 81 source files
Web Client Type-Check:     Passed (0 errors)
Web Client Linter:         Passed (0 errors)
Web Client Build:          Next.js 16.3.3 Turbopack build succeeded
Mobile Client Analyze:     No issues found (0 warnings, 0 errors)
Mobile Client Tests:       3 passed (100%)
Alembic Schema Drift:      No new upgrade operations detected (Zero drift)
Docker Compose Services:   5/5 running and healthy
```
