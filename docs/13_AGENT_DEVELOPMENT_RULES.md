# Digital Student Attendance System
## AI Agent Development Rules

**Version:** 1.0  
**Applies to:** Codex, Google Antigravity, Claude Code, IDE agents, human contributors  
**Purpose:** Prevent uncontrolled AI-generated architecture drift.

---

## 1. Mandatory Reading Order

Before implementing a task, the agent must read relevant project docs.

At minimum:

```text
00_PROJECT_VISION.md
01_PRODUCT_REQUIREMENTS_PRD.md
02_SCOPE_AND_MVP.md
03_USER_ROLES_AND_PERMISSIONS.md
04_ATTENDANCE_RULES.md
05_ANTI_CHEATING_AND_PRESENCE_MODEL.md
06_OFFLINE_AND_SYNC_MODEL.md
07_SYSTEM_ARCHITECTURE.md
08_DOMAIN_MODEL.md
09_DATABASE_SCHEMA.md
10_API_SPECIFICATION.md
12_SECURITY_REQUIREMENTS.md
```

For UI work also read:

```text
11_UI_SCREEN_MAP.md
```

For tests read:

```text
14_TESTING_STRATEGY.md
```

---

## 2. Architecture Is Not Optional

Agents must not change these without an approved architecture decision:

- FastAPI backend
- PostgreSQL primary database
- Next.js PWA
- Flutter mobile app
- Redis
- Modular monolith
- REST `/api/v1`
- Campus-local operational authority
- Docker deployment model
- Three-checkpoint attendance model
- Cryptographic device registration

A proposed change must be documented first in `15_ARCHITECTURE_DECISIONS.md`.

---

## 3. Work Unit

Every implementation request should be treated as:

```text
Requirement
-> Acceptance criteria
-> Plan
-> Implementation
-> Tests
-> Self-review
-> Documentation
```

Do not start broad implementation without a task boundary.

---

## 4. Planning Requirement

For non-trivial tasks, agent must first produce a short implementation plan containing:

1. Files/modules affected
2. Database changes
3. API changes
4. UI changes
5. Security implications
6. Tests
7. Migration/backward compatibility risks

Then implement.

---

## 5. Branching

Recommended branches:

```text
feature/<short-name>
fix/<short-name>
refactor/<short-name>
security/<short-name>
docs/<short-name>
```

Do not make unrelated changes in one branch.

---

## 6. Database Rules

- Every schema change uses Alembic.
- Never edit production DB manually in place of a migration.
- Never delete attendance/audit history to "fix" a bug.
- Add database constraints for critical invariants.
- Test migrations from previous schema.
- Avoid destructive migrations without explicit review.

---

## 7. Backend Rules

- Routes/controllers remain thin.
- Business rules live in services/domain layer.
- Authorization server-side.
- Validate all request bodies.
- Use typed models.
- No direct SQL scattered through route handlers.
- No client-controlled final attendance status.
- Use transactions for related writes.
- Sensitive actions generate audit events.

---

## 8. Attendance Rules

Agents must preserve:

- Three-checkpoint model
- Configurable checkpoint mapping
- Unique student/checkpoint result
- Unique student/session final record
- Token expiry
- Device validation
- Campus presence policy
- Offline source labeling
- Correction history

Do not weaken attendance checks just to make a failing test pass.

---

## 9. Security Rules

Never:

- Disable TLS verification
- Hard-code secrets
- Log passwords/tokens/private keys
- Trust client role
- Trust client device time
- Accept static QR indefinitely
- Remove authorization check to solve an error
- Make admin endpoint public
- Bypass device validation silently

---

## 10. Frontend Rules

### Next.js

- TypeScript strict mode
- Role-aware navigation
- Permission-based UI but server remains authoritative
- RTL support
- Accessibility
- No business-critical logic only in browser

### Flutter

- Business logic separated from widgets
- Native plugins wrapped behind interfaces
- Secure storage for sensitive keys
- SQLite/Drift for controlled local persistence
- Handle offline/local-server states explicitly

---

## 11. API Rules

- API versioned under `/api/v1`.
- Use standard error envelope.
- Use idempotency for retry-sensitive writes.
- Update OpenAPI snapshot/client contracts when endpoint changes.
- Breaking contract requires explicit review.

---

## 12. Testing Requirement

No feature is complete without tests appropriate to its risk.

At minimum:

- Unit tests for business rules
- API integration tests
- Authorization tests
- Database constraint tests

Attendance/security work additionally requires:

- Replay tests
- Duplicate tests
- Wrong device tests
- Wrong class tests
- Closed checkpoint tests
- Offline/sync tests where applicable

---

## 13. Bug Fix Rule

Every meaningful bug fix should include a regression test when feasible.

---

## 14. Definition of Done

A feature is done only when:

- Requirement is implemented.
- Acceptance criteria pass.
- Tests pass.
- Lint/type checks pass.
- Database migration exists if needed.
- Authorization is verified.
- Audit requirements are satisfied.
- Error states are handled.
- Docs updated if behavior changed.
- No unrelated files were modified.
- Agent performed self-review.

---

## 15. Self-Review Checklist

Before completion, agent asks:

- Did I violate architecture?
- Did I create duplicated business logic?
- Did I weaken security?
- Did I forget authorization?
- Did I handle offline state?
- Is operation idempotent?
- Is audit required?
- Are timestamps server-authoritative?
- Are tests sufficient?
- Did I change the API contract?
- Do docs need an update?

---

## 16. Repository Boundaries

Recommended ownership:

```text
apps/web          -> Next.js UI
apps/mobile       -> Flutter
backend/app       -> FastAPI domain/modules
contracts         -> API contracts/generated clients
infra             -> deployment
docs              -> source of truth
tests/e2e         -> cross-system tests
tests/load        -> load tests
tests/security    -> security checks
```

Agents should not place backend business logic in web/mobile folders.

---

## 17. Dependency Rules

Before adding a dependency:

1. Explain why it is needed.
2. Prefer maintained libraries.
3. Avoid overlapping libraries.
4. Pin/lock version.
5. Add tests around critical third-party behavior.
6. Do not introduce a framework for a trivial utility.

---

## 18. Refactoring Rules

Refactor only when:

- Required for current feature
- Fixes clear technical debt
- Covered by tests

Do not perform broad stylistic rewrites during unrelated work.

---

## 19. Production Restrictions

Agents must not:

- Directly alter production data
- Run destructive migrations without approval
- Rotate secrets without operational plan
- Delete backups
- Disable monitoring
- Grant broad permissions to fix access issues

Production changes require explicit human approval.

---

## 20. Recommended Agent Prompt Template

```text
Read the relevant files in /docs before coding.

Task:
<task>

Acceptance criteria:
<criteria>

Rules:
- Preserve architecture.
- Do not modify unrelated modules.
- Use migrations for schema changes.
- Enforce authorization server-side.
- Add appropriate tests.
- Run lint/typecheck/tests.
- Report files changed, tests run, and remaining risks.
```
