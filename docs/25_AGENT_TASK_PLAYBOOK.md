# Digital Student Attendance System
## AI Agent Task Playbook and Execution Templates

**Document Version:** 1.0  
**Status:** Approved Operational Standard  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Playbook Purpose & Governance

This playbook establishes standardized execution templates for AI coding agents (such as Google Antigravity, OpenAI Codex, Claude Code) and human software engineers working on the Digital Student Attendance System.

### The Mandatory 9-Step Agent Workflow
Every task execution must follow these 9 steps without exception:
1. **Read Relevant Docs**: Review authoritative specifications in `docs/` before writing any code.
2. **Produce a Plan**: Formulate an implementation plan containing scope boundaries and verification steps.
3. **Identify Affected Files**: Explicitly list files to be created, modified, or deleted.
4. **Identify Security Impact**: Analyze authorization, token handling, cryptographic keys, and input sanitization.
5. **Identify Database Impact**: Determine if an Alembic migration is required; assess index and concurrency impact.
6. **Implement Only Requested Task**: Do not implement extra features or refactor unrelated modules.
7. **Run Tests**: Execute unit, integration, and lint checks.
8. **Self-Review**: Verify compliance against `docs/13_AGENT_DEVELOPMENT_RULES.md` and `docs/26_DEFINITION_OF_DONE.md`.
9. **Report Changes & Risks**: Summarize modified files, test results, and any residual risks.

---

## 2. Standardized Task Templates

### 2.1 Feature Implementation Template
```text
Task ID: [e.g., TASK-014-04]
Title: [Implement start-session API endpoint]
Required Docs: docs/04_ATTENDANCE_RULES.md, docs/07_SYSTEM_ARCHITECTURE.md, docs/10_API_SPECIFICATION.md

Instructions:
1. Review the required documentation before modifying any code.
2. Formulate an implementation plan with bounded scope.
3. Implement the feature within the designated module (e.g., backend/app/modules/attendance/).
4. Enforce server-side authorization check (e.g., require_permission('attendance:session:start')).
5. Validate all inputs using Pydantic v2 schemas.
6. Emit audit log event for state modification.
7. Add automated unit and integration tests.
8. Run linter, typechecker, and test suite.
9. Provide completion summary: files changed, tests run, and remaining risks.
```

### 2.2 Database Migration Template
```text
Task ID: [e.g., TASK-014-01]
Title: [Create attendance sessions database model and migration]
Required Docs: docs/08_DOMAIN_MODEL.md, docs/09_DATABASE_SCHEMA.md, docs/23_DATABASE_MIGRATION_PLAN.md

Instructions:
1. Inspect the migration sequence in docs/23_DATABASE_MIGRATION_PLAN.md.
2. Define SQLAlchemy 2.0 async model with explicit UUIDv7 primary keys and UTC timestamps.
3. Generate new Alembic revision: alembic revision --autogenerate -m "<name>".
4. Inspect the generated migration script to ensure both upgrade() and downgrade() are clean and reversible.
5. Add explicit foreign key constraints and indexes (e.g., ix_attendance_sessions_class_occurrence_id).
6. Verify migration applies cleanly up and down against PostgreSQL.
7. Never drop historical attendance data.
8. Report model changes and migration checksum.
```

### 2.3 API Implementation Template
```text
Task ID: [e.g., TASK-016-04]
Title: [Create student check-in ingestion endpoint]
Required Docs: docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md, docs/10_API_SPECIFICATION.md

Instructions:
1. Define request and response schemas in backend/app/modules/<module>/schemas.py.
2. Wrap response in standard API envelope {"data": ..., "error": null}.
3. Enforce rate limiting and request idempotency.
4. Verify digital signature or dynamic token server-side.
5. Never trust client device clock; persist server-authoritative UTC timestamp.
6. Export updated OpenAPI contract to contracts/openapi.json.
7. Add integration test covering valid check-in, expired token, and duplicate submission.
```

### 2.4 Bug Fix Template
```text
Task ID: [e.g., FIX-018-02]
Title: [Resolve token drift tolerance issue]
Required Docs: docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md, docs/13_AGENT_DEVELOPMENT_RULES.md

Instructions:
1. Reproduce the defect by writing a failing regression test first.
2. Inspect relevant service logic without altering unaffected subsystems.
3. Apply the minimal necessary correction to satisfy the regression test.
4. Never disable security invariants, token expiration, or authorization checks to resolve a bug.
5. Run full regression test suite to ensure zero unintended side effects.
6. Document root cause, fix rationale, and regression test coverage.
```

### 2.5 Security Review Template
```text
Task ID: [e.g., SEC-030-01]
Title: [Security assessment of authentication and token validation]
Required Docs: docs/05_ANTI_CHEATING_AND_PRESENCE_MODEL.md, docs/12_SECURITY_REQUIREMENTS.md

Instructions:
1. Inspect target endpoints for:
   - Missing or bypassable authorization middleware.
   - Timing attack vulnerabilities in token/password comparisons.
   - Client-side trust vulnerabilities (e.g., client-supplied role or status).
   - SQL injection, NoSQL injection, or parameter tampering.
   - Replay vulnerabilities on dynamic QR or signed payloads.
2. Attempt malicious attack vectors in isolated security tests.
3. Verify rate limiting and security headers.
4. Report vulnerabilities found, CVSS severity estimate, and remediation plan.
```

### 2.6 Test Generation Template
```text
Task ID: [e.g., TEST-017-06]
Title: [Generate policy evaluation unit tests]
Required Docs: docs/04_ATTENDANCE_RULES.md, docs/14_TESTING_STRATEGY.md

Instructions:
1. Identify all edge cases and boundary conditions in target service.
2. Create parameterized test matrix covering:
   - Happy path (standard attendance).
   - Boundary conditions (exactly 75% threshold, 10 min late cutoff).
   - Negative cases (invalid token, unregistered device, closed session).
   - Concurrency / race conditions.
3. Ensure tests run completely in memory or against test database fixture.
4. Verify code coverage meets or exceeds 85% requirement.
```

### 2.7 Refactoring Template
```text
Task ID: [e.g., REFACTOR-002-02]
Title: [Refactor database session dependency injection]
Required Docs: docs/07_SYSTEM_ARCHITECTURE.md, docs/13_AGENT_DEVELOPMENT_RULES.md

Instructions:
1. Ensure full test coverage exists before modifying code.
2. Refactor code structure without changing external API contracts or database schema.
3. Run tests continuously throughout refactoring.
4. Preserve existing comments and docstrings unless directly obsolete.
5. Verify linting, type-checking, and performance metrics.
```

### 2.8 Documentation Update Template
```text
Task ID: [e.g., DOCS-010-02]
Title: [Update API specification with batch endpoints]
Required Docs: docs/10_API_SPECIFICATION.md, docs/15_ARCHITECTURE_DECISIONS.md

Instructions:
1. Verify whether the documentation change reflects an approved Architecture Decision.
2. If changing system invariants or baseline technologies, reject change until an ADR is approved.
3. Maintain exact Markdown formatting, numbering conventions, and table layouts.
4. Update references across cross-referenced documents.
5. Commit with docs(...) conventional commit message.
```

### 2.9 Architecture Review Template
```text
Task ID: [e.g., ARCH-001]
Title: [Review proposed asynchronous notification architecture]
Required Docs: docs/07_SYSTEM_ARCHITECTURE.md, docs/15_ARCHITECTURE_DECISIONS.md

Instructions:
1. Evaluate proposal against approved baseline (modular monolith, local-first campus server).
2. Identify any forbidden patterns (e.g., microservices, external cloud lock-in).
3. Evaluate offline impact, scalability, and operational complexity for local university staff.
4. Draft formal Architecture Decision Record (ADR) following the template in docs/15.
5. Present tradeoffs and submit for human architectural review.
```

### 2.10 Code Review Template
```text
Task ID: [e.g., REVIEW-PR-42]
Title: [Review Pull Request for attendance session state machine]
Required Docs: docs/13_AGENT_DEVELOPMENT_RULES.md, docs/26_DEFINITION_OF_DONE.md

Instructions:
1. Check that code strictly satisfies task acceptance criteria.
2. Verify zero secrets or private keys are committed.
3. Verify server-authoritative security:
   - Client cannot mark itself Present.
   - Timestamps are server-generated UTC.
   - Authorization middleware is present on every route.
4. Verify tests exist, pass, and cover negative/edge conditions.
5. Verify database migrations are reversible.
6. Provide specific, actionable review feedback.
```
