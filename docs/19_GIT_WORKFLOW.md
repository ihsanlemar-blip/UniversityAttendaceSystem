# Digital Student Attendance System
## Git Workflow and Version Control Policy

**Document Version:** 1.0  
**Status:** Approved Engineering Policy  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Overview and Philosophy

This repository follows a streamlined, trunk-based branching model with short-lived feature branches and protected `main`. Unnecessary Git Flow complexity (such as long-lived `develop`, `release`, and `hotfix` branches) is intentionally avoided in accordance with modern engineering standards.

Every change in the repository must be:
1. Tied to an approved Epic or Task ID (e.g., `TASK-014-02`).
2. Developed on an isolated topic branch.
3. Validated by automated CI checks.
4. Reviewed and merged into `main` via Pull Request with a squash or linear merge strategy.

---

## 2. Branch Naming Conventions

All branches created by developers or AI coding agents must follow the standard prefixes:

| Branch Pattern | Purpose | Example |
| :--- | :--- | :--- |
| `main` | Production-ready protected trunk | `main` |
| `feature/<task-id>-<short-slug>` | New capabilities or functional enhancements | `feature/TASK-003-01-user-model` |
| `fix/<task-id>-<short-slug>` | Bug fixes and defect corrections | `fix/TASK-014-06-session-timer` |
| `security/<task-id>-<short-slug>` | Security vulnerability remediation and hardening | `security/TASK-030-01-rate-limiting` |
| `refactor/<task-id>-<short-slug>` | Code refactoring without behavioral change | `refactor/TASK-002-02-session-pool` |
| `docs/<task-id>-<short-slug>` | Architecture, specification, and README updates | `docs/TASK-001-02-git-workflow` |

Branches must be deleted immediately upon successful merge into `main`.

---

## 3. Commit Message Standards

Commit messages must adhere strictly to the **Conventional Commits 1.0.0** specification, prefixed with the relevant task identifier.

### Format
```text
<type>(<scope>): [<task-id>] <imperative description>

[optional body explaining motivation and architectural context]

[optional footer referencing breaking changes or issues]
```

### Allowed Types
- `feat`: New feature or capability
- `fix`: Defect or bug repair
- `docs`: Documentation changes only
- `refactor`: Code modification that neither fixes a bug nor adds a feature
- `test`: Adding or correcting tests without modifying production code
- `infra`: Infrastructure, Docker, Nginx, or CI/CD workflow updates
- `chore`: Dependency updates, formatting, or repository housekeeping

### Examples
```text
feat(attendance): [TASK-014-04] implement session start REST endpoint

Validates lecturer assignment and schedule occurrence before transitioning
session state from SCHEDULED to ACTIVE. Integrates with audit logging.
```

```text
fix(security): [TASK-018-02] correct HMAC token drift window tolerance

Allows +/- 1 rotation step (30s) to account for clock skew on campus local network.
```

---

## 4. Protected Main Branch Rules

The `main` branch represents the deployable, authoritative baseline of the Digital Student Attendance System.

### Protections Configured
1. **Direct Pushes Disabled**: No developer or AI agent may push directly to `main`. All changes enter via Pull Requests.
2. **Required Status Checks**:
   - `backend-lint-and-test`: Ruff, MyPy, pytest passing with 100% green status.
   - `web-lint-and-build`: ESLint, TypeScript check, Next.js build succeeding.
   - `flutter-analyze-and-test`: `flutter analyze` and `flutter test` passing.
   - `security-secret-scan`: Gitleaks / TruffleHog scan detecting zero committed credentials.
3. **Required Code Review**: At least one human lead approval required before merge.
4. **Linear History Enforced**: Fast-forward or squash-merge only; merge commits disabled to maintain clean bisectable Git history.

---

## 5. Pull Request (PR) Lifecycle

1. **Branch Creation**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/TASK-014-04-session-api
   ```
2. **Local Verification Before Push**:
   - Run linter and formatter.
   - Run relevant test suite.
   - Ensure working tree is clean.
3. **PR Submission**:
   - Open Pull Request targeting `main`.
   - Title must follow Conventional Commits standard with Task ID.
   - PR description must provide:
     - Task ID and link to specification.
     - Summary of changes.
     - Confirmation of architectural safeguards (e.g., no client-side final attendance).
     - Test evidence.
4. **CI Execution**: GitHub Actions executes all test matrices automatically.
5. **Review & Approval**: Reviewers verify adherence to `docs/13_AGENT_DEVELOPMENT_RULES.md` and `docs/26_DEFINITION_OF_DONE.md`.
6. **Merge**: Squash and merge into `main` with formatted commit message.

---

## 6. Release Tagging & Releases

When milestone or version gates are reached (per `docs/27_RELEASE_AND_VERSIONING_STRATEGY.md`):
1. A Git annotated tag is created on `main`:
   ```bash
   git tag -a v0.1.0 -m "Milestone 3 — Repository & Implementation Blueprint Baseline"
   git push origin v0.1.0
   ```
2. Release tags follow Semantic Versioning (`vMAJOR.MINOR.PATCH`).
3. Production releases are never created automatically by CI; they require manual human approval and signing.

---

## 7. AI Agent Version Control Rules

AI coding agents (Codex, Google Antigravity, Claude Code) operating in this repository must strictly adhere to the following rules:

1. **Never Bypass Git Protection**: Agents must never run `--force` pushes or modify branch protection rules.
2. **Never Commit Secrets**: Agents must inspect diffs for `.env`, private keys, database passwords, or JWT secrets before staging.
3. **Atomic Scope**: Agents must modify only files directly relevant to the assigned Task ID. Unrelated formatting or refactoring across other packages is strictly forbidden.
4. **Documentation Integrity**: If an agent alters a data model or API route, it must update the corresponding OpenAPI contract and documentation in `docs/` within the same commit or PR.
5. **Verify Clean Git Tree**: After completing a task, the agent must run `git status` and verify that untracked temporary files or build artifacts are excluded.
