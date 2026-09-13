# Digital Student Attendance System
## Architecture Decision Records (ADR)

**Version:** 1.0  
**Purpose:** Record major technical decisions so AI agents and developers do not casually change the architecture.

---

# ADR-001 — Use a Modular Monolith

**Status:** Accepted

## Decision

Build one FastAPI backend as a modular monolith rather than microservices.

## Rationale

- Initial scale does not require microservices.
- Easier deployment on a university local server.
- Easier offline/local operation.
- Lower operational complexity.
- Easier for a small team and AI coding agents.
- Module boundaries still permit future extraction.

## Consequence

No independent microservice may be introduced without a new ADR.

---

# ADR-002 — Campus Server Is the V1 Operational Authority

**Status:** Accepted

## Decision

The local university server is authoritative for attendance operations.

## Rationale

Internet is unreliable. Attendance must continue locally.

## Consequence

Cloud services must not be required for normal attendance.

---

# ADR-003 — Hybrid PWA + Flutter Clients

**Status:** Accepted

## Decision

Use:

- Next.js responsive PWA for administration, lecturers, reporting, and general student self-service.
- Flutter app for attendance-sensitive mobile functions.

## Rationale

A PWA works well across Windows/Linux and general mobile access, but high-confidence Bluetooth/device-bound attendance needs more reliable native capabilities.

---

# ADR-004 — FastAPI Backend

**Status:** Accepted

## Decision

Use FastAPI/Python.

## Rationale

- Strong typed API models
- Automatic OpenAPI
- Good fit for AI-assisted development
- Fast development
- Suitable for modular service architecture
- Good testing ecosystem

---

# ADR-005 — PostgreSQL Primary Database

**Status:** Accepted

## Decision

Use PostgreSQL for campus operational data.

## Rationale

- Strong relational integrity
- Transactions
- Mature indexing/query support
- JSONB where needed
- Reliable backup tooling
- Good fit for academic/attendance relations

---

# ADR-006 — Redis for Transient State

**Status:** Accepted

## Decision

Use Redis for:

- Caching
- Rate limiting
- short-lived transient state
- Celery broker/backing where appropriate

Redis is not the system of record.

---

# ADR-007 — REST API First

**Status:** Accepted

## Decision

Use versioned REST API under `/api/v1`.

## Rationale

- Easy web/mobile integration
- Strong FastAPI/OpenAPI support
- Simpler than GraphQL for current domain
- Easier offline client contracts

---

# ADR-008 — Monorepo

**Status:** Accepted

## Decision

Keep web, mobile, backend, infra, contracts, docs, and cross-system tests in one repository initially.

## Rationale

- Easier synchronized changes
- Easier AI-agent context
- Easier versioned documentation
- Easier CI

---

# ADR-009 — Three Checkpoints Are Core Domain Behavior

**Status:** Accepted

## Decision

Start, middle, and end checkpoints are first-class domain entities.

## Rationale

They are not merely UI steps; they provide evidence for late arrival and early departure.

## Consequence

Do not model attendance as a single boolean column.

---

# ADR-010 — Attendance Policy Is Configurable

**Status:** Accepted

## Decision

Do not hard-code:

- 75% threshold
- 10-minute late rule
- 3–5 minute duration
- 20–30 second token rotation
- 2-of-3 interpretation

These are defaults/policies.

---

# ADR-011 — Cryptographic Device Registration

**Status:** Accepted

## Decision

Use app-generated asymmetric device keys rather than relying only on hardware identifiers.

## Rationale

- Better security
- Better privacy
- More portable across modern mobile platforms
- Supports signed attendance requests

---

# ADR-012 — Bluetooth Is Supporting Evidence

**Status:** Accepted

## Decision

Bluetooth will contribute to presence verification but will not alone determine attendance.

## Rationale

Bluetooth can fail legitimately and can be manipulated.

---

# ADR-013 — GPS Is Not Primary

**Status:** Accepted

## Decision

Do not require GPS for ordinary V1 attendance.

## Rationale

- Indoor accuracy limitations
- Spoofing
- Privacy
- Battery impact

GPS may be optional secondary evidence.

---

# ADR-014 — No Face Recognition in V1

**Status:** Accepted

## Decision

Exclude facial recognition/selfie verification.

## Rationale

- Privacy
- Operational complexity
- Bias/error risk
- Not necessary for initial anti-cheating design

---

# ADR-015 — Transactional Outbox for Cloud Sync

**Status:** Accepted

## Decision

Use a transactional outbox/inbox pattern for reliable replication.

## Rationale

Avoid losing sync events when business transaction commits but network/cloud send fails.

---

# ADR-016 — Class Occurrence Separate from Timetable Rule

**Status:** Accepted

## Decision

Represent recurring schedule and concrete class occurrence separately.

## Rationale

Needed for:

- cancellation
- rescheduling
- substitute lecturer
- room change
- make-up class
- attendance linkage

---

# ADR-017 — Flexible Academic Unit Hierarchy

**Status:** Accepted

## Decision

Use a parent-child `AcademicUnit` structure with types rather than hard-requiring Faculty -> Department -> Program.

## Rationale

University structures differ and may omit levels.

---

# ADR-018 — Physical QR Card Is Staff-Scanned Fallback

**Status:** Accepted

## Decision

Physical card is a fallback credential normally scanned by lecturer/authorized staff.

## Rationale

Allowing remote self-submission of a static card image would enable proxy attendance.

---

# ADR-019 — Store Timestamps in UTC

**Status:** Accepted

## Decision

Persist UTC timestamps; render using university timezone.

## Rationale

Avoid ambiguity and support future multi-campus use.

---

# ADR-020 — Dockerized Local Deployment

**Status:** Accepted

## Decision

Deploy local services with Docker containers.

## Rationale

- Repeatable installation
- Easier backup/recovery
- Easier upgrades
- Consistent staging/production environments

---

# ADR-021 — Version 1 Is Single-University but Future-Aware

**Status:** Accepted

## Decision

Include `university_id` boundaries and reusable organization design but do not build full SaaS tenancy/billing/control plane in V1.

## Rationale

Avoid both extremes:

- hard-coding one university forever
- overengineering SaaS before the first pilot

---

# ADR-022 — Existing Finance/Exam Systems Will Be Integrated, Not Rebuilt

**Status:** Accepted

## Decision

V1 attendance remains independent. Future integration uses approved APIs/imports/controlled connectors.

## Rationale

The university already has financial and examination systems.

---

# ADR-023 — AI Agents Must Follow Documentation

**Status:** Accepted

## Decision

Project documentation is architectural source of truth.

AI agents cannot silently change architecture to simplify implementation.

---

## Change Process

To change an accepted ADR:

1. Create a new ADR.
2. Explain the problem.
3. List alternatives.
4. Describe migration impact.
5. Obtain human approval.
6. Update affected documentation.
7. Implement only after approval.
