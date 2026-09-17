# Digital Student Attendance System
## Milestone 17 Manifest — Complete MVP User Experience

**Generated At:** 2026-09-17  
**Feature Branch:** `feature/task-015-complete-mvp-user-experience`  
**Milestone:** 17 — Complete MVP User Experience  

---

## 1. Inventory of Files Created / Modified

### 1.1 Web Application (`apps/web/`)
- `apps/web/src/lib/i18n/types.ts`: Strongly typed locale definition (`SupportedLocale`), text direction (`'ltr' | 'rtl'`), metadata, and strongly typed translation key union `TranslationKey`.
- `apps/web/src/lib/i18n/translations/en.ts`: Complete English dictionary.
- `apps/web/src/lib/i18n/translations/fa-AF.ts`: Authentic Afghan Dari dictionary preserving Afghan academic terminology (پوهنتون, پوهنځی, څانګه, کریدت, سمستر, حاضر, ناوخته, غیرحاضر, معذور).
- `apps/web/src/lib/i18n/translations/ps.ts`: Authentic Pashto dictionary preserving Afghan academic terminology.
- `apps/web/src/lib/i18n/error-map.ts`: Safe error mapper transforming backend error codes into user-friendly titles and guidance without database or stack trace leakage.
- `apps/web/src/context/language-context.tsx`: `LanguageProvider` and `useLanguage()` managing active locale, directionality, and synchronizing with `document.documentElement.lang` and `document.documentElement.dir`.
- `apps/web/src/components/layout/language-selector.tsx`: Accessible language switcher dropdown.
- `apps/web/src/components/layout/top-nav.tsx`: Embedded `LanguageSelector` in header.
- `apps/web/src/app/layout.tsx`: Wrapped application in `LanguageProvider`.
- `apps/web/src/app/login/page.tsx`: Embedded language selector, converted strings to `useLanguage()`, and updated inputs with logical styling (`start-0`, `end-0`, `ps-9`, `pe-3`).
- `apps/web/src/app/change-password/page.tsx`: Converted to `useLanguage()`, updated inputs with logical classes, embedded language selector.
- `apps/web/src/app/lecturer/session/[id]/page.tsx`: Dynamic session controller with real-time QR rotation, synchronized BLE broadcasting, live attendance roster, factor badges, and manual roll-call override modal.
- `apps/web/src/app/admin/attendance/reviews/page.tsx`: Centralized absence excuse and attendance correction review queue with batch actions and audit justification.

### 1.2 Mobile Client (`apps/mobile/`)
- `apps/mobile/lib/core/i18n/app_language.dart`: `AppLanguage` enum (`en`, `fa`, `ps`) with metadata, native display labels, and text direction.
- `apps/mobile/lib/core/i18n/translations_en.dart`: English translation dictionary.
- `apps/mobile/lib/core/i18n/translations_fa.dart`: Authentic Afghan Dari dictionary preserving Afghan academic terminology.
- `apps/mobile/lib/core/i18n/translations_ps.dart`: Authentic Pashto dictionary preserving Afghan academic terminology.
- `apps/mobile/lib/core/i18n/app_strings.dart`: Centralized `AppStrings` accessor and safe backend error mapper.
- `apps/mobile/lib/core/i18n/locale_provider.dart`: Riverpod `LocaleNotifier` persisting language choice via `FlutterSecureStorage` key `dsas_app_language`.
- `apps/mobile/lib/widgets/language_selector_sheet.dart`: Accessible modal bottom sheet for selecting English, Dari, or Pashto.
- `apps/mobile/lib/screens/student_home_screen.dart`: Multi-language support, RTL layout wrapping, language toggle action in AppBar, localized status cards and enrolled courses list.
- `apps/mobile/lib/screens/student_qr_scanner_screen.dart`: Dynamic camera viewfinder, BLE observation indicators, error mapping cards, Semantics tags.
- `apps/mobile/test/localization_test.dart`: 10 comprehensive tests validating language properties, dictionary parity, Afghan academic terms, safe error resolver, and RTL UI rendering.

### 1.3 Offline Mobile Storage Architecture Note
- Mobile offline outbox and permit storage remains the **atomic JSON store** (`apps/mobile/lib/core/offline/offline_storage.dart`) established in Milestone 12.
- Migration to **Drift/SQLite** is explicitly deferred to **Milestone 18 pre-pilot hardening**.
- The M17 release does NOT use Drift/SQLite.

### 1.4 Documentation & Tooling
- `docs/55_MILESTONE_17_COMPLETE_MVP_USER_EXPERIENCE.md`: Comprehensive Milestone 17 specification, offline storage decision, and manual acceptance gates.
- `docs/MILESTONE_17_MANIFEST.md`: Inventory of all changes, tests, and verifications.
- `docs/56_NEXT_IMPLEMENTATION_TASK.md`: Explicit handoff strictly to Milestone 18.
- `scripts/check_docs.py`: Updated to validate specifications up to prefix 56 and manifests up to M17.

---

## 2. Test Verification Summary

| Target | Test Suite / Check | Result |
| :--- | :--- | :--- |
| **Mobile Client** | `dart format lib/ test/` | Clean (0 changed) |
| **Mobile Client** | `flutter analyze` | No issues found (0 warnings, 0 errors) |
| **Mobile Client** | `flutter test` (all 79 tests) | 79 / 79 PASSED |
| **Web Frontend** | `npm run type-check` | Clean (0 errors) |
| **Web Frontend** | `npm run lint` | Clean (0 errors) |
| **Web Frontend** | `npm run build` | Clean production build (all routes prerendered) |
| **Backend API** | `ruff format --check backend/` | Clean |
| **Backend API** | `ruff check backend/` | Clean |
| **Backend API** | `mypy backend` | Strict typecheck passed (0 errors) |
| **Database** | `alembic -c backend/migrations/alembic.ini check` | Head `013_imports_administration (head)`, 0 drift |
| **CI Matrix** | Test file partitioning audit | 72 / 72 test files partitioned (0 missing, 0 duplicates) |
| **Governance** | `scripts/check_secrets.py` | 0 secrets found |
| **Governance** | `scripts/check_docs.py` | Specifications 00–56 and manifests M3–M17 validated |

---

## 3. Outstanding Pre-Pilot Acceptance Gates (Carried to M18/M19)

1. **M11 BLE Physical-Device Acceptance**: Physical radio testing in lecture halls with real multi-device concurrent advertising.
2. **M12 Offline Field/Device Acceptance**: Physical testing of classroom network blackouts, battery drops, and server outbox reconciliation.
3. **M13 Device Registration/Replacement Acceptance**: Physical enrollment of hardware keys and administrative re-binding approvals.
4. **M15 Attendance Operations Workflow Acceptance**: Real-world excuse triage, dispute resolution, and audit ledger inspection.
5. **M16 Import/Report Workflow Acceptance**: Production registrar spreadsheet imports and ministerial reporting exports.
6. **M17 End-to-End MVP UX Acceptance**: Student and faculty usability validation on real Android hardware across Dari, Pashto, and English.
