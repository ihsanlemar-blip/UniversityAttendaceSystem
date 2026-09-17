# Next Implementation Task: Milestone 17 — Complete MVP User Experience

**Status:** Planned / Up Next (Do NOT implement in Milestone 16 task)  
**Applies to:** Next Coding Agent Milestone Handoff  
**Quality Standard:** [docs/26_DEFINITION_OF_DONE.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/26_DEFINITION_OF_DONE.md)  

---

## 1. Task Objective

Execute **Milestone 17: Complete MVP User Experience** for the Digital Student Attendance System. Milestone 17 consolidates the comprehensive backend infrastructure, verification services, operational workflows, and reporting engines built across Milestones 1 through 16 into a cohesive, production-ready, bilingually localized, and polished user experience across both Web and Mobile platforms.

---

## 2. Invariants & Guardrails (Mandatory)

1. **Do NOT Alter Domain Invariants**:
   - Client cannot mark itself present; authoritative UTC server clock sole authority.
   - Dual-factor token/BLE verification rules remain inviolable.
   - Append-only immutable audit ledgers and revision history remain protected.
2. **Preserve Database Schema Integrity**:
   - Zero unauthorized schema changes. Any minor UI persistence requirements must use explicit Alembic migrations.
3. **Preserve Fast Testing & CI Matrix**:
   - Maintain 4-shard GitHub Actions test runner with real PostgreSQL 16 and Redis 7 containers.
   - Zero real-world sleeps (`time.sleep` / `asyncio.sleep`).
4. **No Destructive Operations**:
   - Preserve all existing tests and features; no disabling tests or linting to expedite delivery.

---

## 3. Anticipated Milestone 17 Scope

1. **Unified Role Dashboards**:
   - **Student Dashboard**: Consolidated view of real-time attendance standing, upcoming schedule, active session check-in prompts (QR / BLE), and open correction/excuse statuses.
   - **Lecturer Dashboard**: Active course offerings, current session controller (start/pause/stop broadcast), live attendance verification roll call, and pending correction/excuse review queues.
   - **Administrator Dashboard**: Institutional attendance KPIs, device registration approvals, import center shortcuts, security audit logs, and policy management.
2. **Comprehensive Localization & RTL**:
   - Full bilingual localization support for **Pashto, Dari, and English**.
   - Bidirectional layout mirroring (RTL for Pashto/Dari, LTR for English) across Next.js Web and Flutter Mobile.
   - High-quality academic terminology dictionaries.
3. **UX State Completeness**:
   - Exhaustive coverage of **Loading States** (skeletons, spinners), **Empty States** (no classes scheduled, zero attendance records, empty review queues), and **Error States** (network offline, permission denied, session expired).
   - Onboarding and first-time user guidance for student device pairing and lecturer attendance broadcasting.
4. **Interface Polish & Mock Removal**:
   - Clean removal of all placeholder/mock interfaces, sample arrays, and temporary diagnostic cards across web and mobile.
   - Seamless navigation consistency, responsive layouts (mobile, tablet, desktop web), and WCAG 2.1 AA accessibility compliance.
5. **Integrated MVP Walkthrough**:
   - End-to-end automated walkthrough verifying the full university lifecycle: Institutional Import $\rightarrow$ Timetable Schedule $\rightarrow$ Session Activation $\rightarrow$ QR/BLE Verification $\rightarrow$ Real-time Absence/Excuse Operations $\rightarrow$ Reporting & Official Export.

---

> [!WARNING]
> Do NOT begin implementation of Milestone 17 in this session. Milestone 16 must first complete all verification gates, CI runs, and merge to `main`.
