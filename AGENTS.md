# Digital Student Attendance System
## AI Coding Agent Operational Directives & Invariants

**Applies to:** Google Antigravity, OpenAI Codex, Claude Code, GitHub Copilot, and human developers.  
**Authoritative Reference:** [docs/13_AGENT_DEVELOPMENT_RULES.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/13_AGENT_DEVELOPMENT_RULES.md)  
**Quality Standard:** [docs/26_DEFINITION_OF_DONE.md](file:///e:/01_Projects/UniversityAttendaceSystem/docs/26_DEFINITION_OF_DONE.md)  

---

## 1. Mandatory Reading Requirement

Before writing or modifying any code, the agent **MUST** inspect the relevant specification documents inside `docs/`.
At minimum:
- `docs/00_PROJECT_VISION.md`
- `docs/01_PRODUCT_REQUIREMENTS_PRD.md`
- `docs/04_ATTENDANCE_RULES.md`
- `docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md`
- `docs/07_SYSTEM_ARCHITECTURE.md`
- `docs/08_DOMAIN_MODEL.md`
- `docs/09_DATABASE_SCHEMA.md`
- `docs/13_AGENT_DEVELOPMENT_RULES.md`
- `docs/15_ARCHITECTURE_DECISIONS.md`

---

## 2. Fundamental Attendance Safeguards & Invariants

> [!CAUTION]
> The following invariants are absolute. Any pull request or commit violating these invariants will be rejected:

1. **Client Cannot Mark Itself Present**: The mobile app and web client submit evidence (tokens, signatures, telemetry) to the server. The server attendance engine alone evaluates evidence and determines attendance status.
2. **Attendance Depends on Server/Domain Validation**: Attendance state transitions (`PRESENT`, `LATE`, `ABSENT`, `EXCUSED`) are executed strictly within server domain services.
3. **Student Device Clock Is NOT Authoritative**: Client timestamps are recorded for diagnostic telemetry only. The university server's UTC clock is the sole authority for checkpoint windows and token validity.
4. **Expired Dynamic QR/Tokens Cannot Grant Attendance**: Checkpoint tokens rotate every 20–30 seconds. Tokens presented outside the allowed tolerance window (±1 step) are rejected unconditionally.
5. **No Duplicate Checkpoint Credit**: A student cannot receive multiple successful check-in credits for the same checkpoint in an attendance session.
6. **Corrections Cannot Erase History**: When an attendance record is corrected or excused post-session, the historical record and audit trail remain intact. A new revision record is created.
7. **Offline Events Remain Identifiable**: Any attendance evidence captured offline carries explicit metadata (`OFFLINE_CAPTURED`) and undergoes server reconciliation.
8. **Manual Attendance Overrides Remain Identifiable**: When a lecturer or administrator manually marks a student present, the action requires a recorded justification and logs the actor's ID in the immutable audit ledger.

---

## 3. Strict Prohibitions (Never Do)

1. **NEVER change system architecture without an approved ADR**:
   - Do NOT introduce microservices, GraphQL, MongoDB, Firebase as primary backend, Supabase as primary backend, or face recognition.
2. **NEVER commit real secrets**:
   - No passwords, private keys, API secrets, or JWT keys in code, tests, or documentation.
3. **NEVER disable security or tests to make a build pass**:
   - Do NOT remove authorization middleware (`require_permission`) to solve access errors.
   - Do NOT delete or bypass failing unit/integration tests.
4. **NEVER execute raw manual database edits**:
   - All schema modifications must be versioned Alembic migrations with both `upgrade()` and `downgrade()`.
5. **NEVER delete audit history**:
   - The `audit_logs` table is append-only and immutable.
6. **NEVER perform destructive operations in production**:
   - Do not drop tables or truncate data in production environments.

---

## 4. Execution Workflow

When implementing any task:
1. Follow the **9-Step Workflow** in `docs/25_AGENT_TASK_PLAYBOOK.md`.
2. Restrict edits strictly to files permitted in the task boundary.
3. Format code (`ruff format`, `Prettier`, `dart format`).
4. Run tests and typecheckers.
5. Verify compliance with `docs/26_DEFINITION_OF_DONE.md`.
