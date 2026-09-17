# Milestone 17 — Complete MVP User Experience

**Status:** IMPLEMENTED & SOFTWARE VERIFIED  
**Applies to:** Full-Stack Web Console & Mobile Client  
**Quality Standard:** [docs/26_DEFINITION_OF_DONE.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/26_DEFINITION_OF_DONE.md)  
**Authoritative Reference:** [AGENTS.md](file:///e:/01_Projects/UniversityAttendaceSystem/AGENTS.md)  

---

## 1. Executive Summary & Objective

Milestone 17 delivers the complete, polished MVP User Experience for the Digital Student Attendance System. It connects all foundational systems built across Milestones 1 through 16—including session management, dynamic rotating QR tokens, dual-factor BLE presence broadcasting and verification, offline cryptographic claims, device hardware trust, post-session review workflows, institutional imports, and threshold reporting—into a cohesive, accessible, bilingually localized, and responsive multi-platform user experience.

Primary Languages Supported:
1. **English (`en`)**: System default, LTR.
2. **Dari (`fa-AF` / `fa`)**: Afghan Persian, authentic Afghan academic terminology, RTL.
3. **Pashto (`ps`)**: Afghan Pashto, authentic Afghan academic terminology, RTL.

---

## 2. Invariant Adherence & Architectural Principles

The implementation of Milestone 17 strictly upholds every core attendance invariant:

1. **Client Cannot Mark Itself Present (INV-01)**: The client application (both Web and Mobile) submits cryptographically verifiable evidence (tokens, BLE beacon observations, hardware signatures, telemetry). Only the server-side attendance engine evaluates evidence and transitions attendance status.
2. **Server UTC Authoritative (INV-03)**: Client clocks are treated as untrusted diagnostic data. All checkpoint validity windows, rotation intervals, and expiration deadlines are measured strictly against the authoritative university server UTC clock.
3. **Dynamic Token Rotation (INV-04)**: Dynamic QR tokens rotate strictly every 20–30 seconds. Expired tokens cannot grant attendance credit and trigger localized `TOKEN_EXPIRED` cards with retry guidance.
4. **Idempotency & Zero Duplicate Credit (INV-05)**: Duplicate checkpoint submissions within the same window return HTTP 200 with `ALREADY_RECORDED` status, reassuring the student while preventing duplicate credit without penalty.
5. **Corrections & Audit Ledger Immutability (INV-06)**: All manual overrides, reviews, excuses, and policy changes preserve historical revisions in the append-only `audit_logs` table.
6. **Explicit Offline Identification (INV-07)**: Attendance claims recorded offline carry `OFFLINE_CAPTURED` metadata and require server-side cryptographic reconciliation before credit is formalized.
7. **Safe Error Mapping**: Structured backend error codes (`TOKEN_EXPIRED`, `CHECKPOINT_NOT_OPEN`, `DEVICE_NOT_REGISTERED`, `BLE_REQUIRED`, `CAMPUS_NETWORK_NOT_DETECTED`, etc.) are resolved into localized user-friendly titles and recommendations without exposing SQL syntax, table structures, or stack traces.

---

## 3. Localization & RTL Architecture

### 3.1 Afghan Academic Terminology vs. Iranian Substitutions

All Dari and Pashto translations adhere strictly to Afghan higher education standards:

| Concept | English | Afghan Dari | Afghan Pashto | Prohibited Iranian Term |
| :--- | :--- | :--- | :--- | :--- |
| **Institution** | University | پوهنتون | پوهنتون | دانشگاه |
| **Faculty** | Faculty | پوهنځی | پوهنځی | دانشکده |
| **Department** | Department | څانګه / دیپارتمنت | څانګه | گروه آموزشی |
| **Credit** | Credit | کریدت | کریدت | واحد |
| **Term** | Semester | سمستر | سمستر | ترم |
| **Morning Shift** | Morning Shift | تایم سهارنی | سهارنی تایم | نوبت صبح |
| **Afternoon Shift**| Afternoon Shift | تایم بعد از ظهر | ماسپښین تایم | نوبت بعد از ظهر |
| **Present** | Present | حاضر | حاضر | حاضر |
| **Late** | Late | ناوخته | ناوخته | با تأخیر |
| **Absent** | Absent | غیرحاضر | غیرحاضر | غایب |
| **Excused** | Excused | معذور | معذور | موجه |

### 3.2 Web Frontend (`apps/web`)

- **Types & Enums**: `SupportedLocale` (`'en' | 'fa-AF' | 'ps'`), `SUPPORTED_LOCALES` dictionary containing directionality (`ltr` or `rtl`) and native display labels.
- **Provider & Hook**: `LanguageProvider` with `useLanguage()` managing active locale, direction, `t()` translator, and `getSafeError()` mapper. State persists in `localStorage` key `dsas_locale` and synchronizes with `document.documentElement.lang` and `document.documentElement.dir`.
- **Selector Component**: `LanguageSelector` dropdown with ARIA accessibility, active state indicator, and keyboard navigation.
- **Logical CSS**: Tailwind CSS logical utilities (`start-0`, `end-0`, `ps-9`, `pe-3`, `ms-*`, `me-*`) ensure clean bidirectional mirroring without layout breakage. Technical elements (numbers, course codes, UUIDs, server times) are isolated in LTR wrappers.

### 3.3 Mobile Client (`apps/mobile`)

- **Types & Enums**: `AppLanguage` (`en`, `fa`, `ps`), `AppLanguageExtension` providing ISO code, `Locale`, native display name, `isRtl` boolean, and `textDirection`.
- **Dictionary Architecture**: `translations_en.dart`, `translations_fa.dart`, and `translations_ps.dart` providing complete parity across all UI strings.
- **Helper & Resolver**: `AppStrings.get(AppLanguage lang)` providing localized string access and `getSafeError(String? errorCode)` user-safe error resolution.
- **Persistence Provider**: `locale_provider.dart` using `StateNotifier` and `FlutterSecureStorage` key `dsas_app_language`.
- **UI Switching**: `showLanguageSelectorSheet` modal bottom sheet and AppBar language toggle with Semantics accessibility headers.

---

## 4. End-to-End Persona Workflows

### 4.1 Student Experience
- **Authentication & Security**: Authentication, session management, and mandatory first-login password change, primary device trust key registration (Ed25519) in secure hardware keystore.
- **Home Dashboard**: Real-time attendance rate, Good Standing / Warning / Critical standing badges (or neutral N/A when zero eligible sessions), upcoming classes, and quick action cards.
- **Live Check-In**: Dynamic QR scanner with real-time camera viewfinder, simultaneous classroom BLE presence beacon observation, and instant feedback cards (`Attendance Confirmed`, `Already Recorded`, `Saved for Synchronization`, `Token Expired`).
- **Ledger & Requests**: History of all class sessions, filterable by status, with excuse submission forms and revision timeline inspection.

### 4.2 Lecturer Experience
- **Session Controller**: Course selection, timetable schedule matching, session activation with configurable checkpoint windows.
- **Dual-Factor Broadcasting**: Real-time dynamic rotating QR projection (20s cycle) and synchronized BLE presence beacon advertisement.
- **Live Roll Call**: Real-time student verification count, check-in factor breakdown (QR only vs QR+BLE), and manual attendance marking with mandatory justification.
- **Excuse Reviews**: Dedicated review tab to approve, reject, or request information on student absence excuse requests.

### 4.3 Administrator Experience
- **Import Center**: Academic structure, students, lecturers, courses, offerings, and timetable schedule ingestion from CSV/XLSX with strict/partial commit modes.
- **Attendance Reporting**: Institutional analytics, offering attendance rosters, dynamic threshold indicators (`ABOVE_THRESHOLD`, `NEAR_THRESHOLD`, `BELOW_THRESHOLD`, `NOT_APPLICABLE`), and formula-injection-safe CSV/XLSX exports.
- **Policy Management**: Prospective attendance threshold sliders, grace periods, correction windows, and mandatory audit logging.
- **Device Management**: Primary device trust approval queue, fingerprint inspection, device revocation, and hardware keystore status monitoring.

---

## 5. Offline Mobile Storage Architecture Decision

1. **Current Implementation**: The mobile client offline storage layer (`apps/mobile/lib/core/offline/offline_storage.dart`) uses the atomic JSON-based outbox and permit cache established in Milestone 12. It guarantees atomic file writes via temporary file swapping (`File.rename`), strict local account isolation by student ID, and survivability across application restarts.
2. **Architectural Evaluation**: In Milestone 17 Part 2, migration to Drift/SQLite was evaluated. To prevent introducing schema churn, C-compiler dependencies, and native binding volatility during a pure UX/frontend milestone, the atomic JSON store was intentionally preserved for the MVP software release.
3. **Formal Decision & Handoff**: The current implementation is **NOT Drift/SQLite**. Migration of offline outbox and permit storage to Drift/SQLite is formally recorded as a **mandatory Milestone 18 pre-pilot hardening requirement**.

---

## 6. Verification & Test Partitioning Audit

### 6.1 Test Sharding Audit
The complete backend regression test suite of 72 test files was audited against `.github/workflows/ci.yml`.
- **Total Test Files on Disk**: 72
- **Total Test Files in CI Shards**: 72 (18 files per shard across 4 parallel jobs)
- **Duplicates**: 0
- **Missing**: 0
- **Schema Drift**: `alembic check` verified 0 unapplied revisions and 0 schema drifts against Head `013_imports_administration`.

### 6.2 Verification Summary
- **Backend**: Ruff linting, formatting, Mypy strict typecheck, and sharded pytest suite passing (all 4 shards green).
- **Web**: ESLint, TypeScript `tsc --noEmit`, Next.js production build passing.
- **Mobile**: Dart formatting (`dart format`), Flutter static analysis (`flutter analyze`), and comprehensive test suite (`flutter test`, 79/79 tests passing).

---

## 7. Outstanding Physical & Field Acceptance Gates (Mandatory Pre-Pilot Checklist)

Software implementation of Milestone 17 is 100% complete and automated quality gates are green. However, physical and operational acceptance must be explicitly executed on real devices in production-like campus environments before university deployment:

1. **M11 BLE Physical-Device Acceptance**: Radio transmission, RSSI calibration, and peripheral advertising verification with physical Android and iOS hardware inside real concrete lecture halls.
2. **M12 Offline Field/Device Acceptance**: Physical testing of prolonged classroom network dropouts, battery depletion survivability, and batched reconciliation against production server.
3. **M13 Device Registration/Replacement Acceptance**: Physical enrollment of hardware keys (Android Keystore / iOS Secure Enclave), device replacement requests, and administrative re-binding approvals.
4. **M15 Attendance Operations Workflow Acceptance**: Real-world faculty excuse adjudication, student dispute resolution, and audit ledger inspection with university academic staff.
5. **M16 Import/Report Workflow Acceptance**: End-to-end institutional onboarding with real university registrar CSV/XLSX spreadsheets, messy data normalization, and ministry export compliance.
6. **M17 End-to-End MVP UX Acceptance**: Usability acceptance testing with Afghan university students and faculty across low-cost Android hardware in Dari, Pashto, and English.

---

## 8. Definition of Done Compliance

All criteria outlined in `docs/26_DEFINITION_OF_DONE.md` for Milestone 17 are met:
- [x] Zero architecture deviation without ADR.
- [x] Zero plain-text credentials or secret commits.
- [x] Zero bypass of security middleware or permission checks.
- [x] Authentic Afghan academic terminology in Dari and Pashto.
- [x] True bidirectional RTL layout mirroring on web and mobile.
- [x] Safe error mapping without database or stack trace exposure.
- [x] Complete CI matrix green across all 9 GitHub Actions jobs.
- [x] Clean documentation handoff to Milestone 18.
- [x] Explicit preservation of outstanding physical/manual acceptance gates.
