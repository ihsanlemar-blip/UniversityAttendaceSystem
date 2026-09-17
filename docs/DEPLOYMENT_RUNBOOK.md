# Production Deployment Runbook

**Document ID:** `DEPLOYMENT_RUNBOOK`  
**System:** Digital Student Attendance System  
**Target Environment:** Production / Pilot Staging  
**Applicability:** DevOps, Systems Engineers, IT Infrastructure Staff  

---

## 1. Prerequisites

- **Host Operating System:** Linux (Ubuntu 22.04 LTS / Debian 12 / RHEL 9 recommended).
- **Runtime Dependencies:** Docker Engine 24.0+ and Docker Compose v2.20+.
- **Domain & DNS:** Public DNS record (`attendance.university.edu`) pointing to server static IPv4/IPv6.
- **Port Access:** Inbound TCP ports `80` and `443` open on firewall. Internal ports (`5432`, `6379`, `8000`, `3000`) blocked from external access.

---

## 2. Environment Configuration & Secret Generation

1. Clone repository to server root:
   ```bash
   git clone https://github.com/ihsanlemar-blip/UniversityAttendaceSystem.git /opt/attendance-system
   cd /opt/attendance-system
   ```

2. Generate cryptographically strong production secrets:
   ```bash
   # Generate 64-char random hex secrets
   openssl rand -hex 32  # For AUTH_SIGNING_KEY
   openssl rand -hex 32  # For ATTENDANCE_QR_SIGNING_KEY
   openssl rand -hex 32  # For ATTENDANCE_BLE_SIGNING_KEY
   openssl rand -hex 32  # For POSTGRES_PASSWORD
   openssl rand -hex 32  # For REDIS_PASSWORD (optional)
   
   # Generate Ed25519 Keypair for Offline Permits
   openssl genpkey -algorithm Ed25519 -out offline_priv.pem
   openssl pkey -in offline_priv.pem -pubout -out offline_pub.pem
   ```

3. Populate production environment file:
   ```bash
   cp .env.production.example .env.production
   chmod 600 .env.production
   # Edit .env.production with generated secrets and university domain
   ```

---

## 3. Database Migration & Initialization

1. Start backing data stores:
   ```bash
   docker compose -f docker-compose.prod.yml up -d postgres redis
   ```

2. Execute versioned Alembic migrations:
   ```bash
   docker compose -f docker-compose.prod.yml run --rm backend alembic -c backend/migrations/alembic.ini upgrade head
   ```

3. Verify migration version:
   ```bash
   docker compose -f docker-compose.prod.yml run --rm backend alembic -c backend/migrations/alembic.ini current
   # Output must indicate: 014_perf_hardening (head)
   ```

---

## 4. Full Stack Startup & Health Verification

1. Start all application containers:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

2. Inspect container statuses:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   # Verify backend, postgres, redis, web, worker, and caddy are healthy
   ```

3. Verify operational endpoints:
   ```bash
   # Liveness
   curl -I https://attendance.university.edu/health/live
   # HTTP/2 200 OK
   
   # Readiness
   curl -s https://attendance.university.edu/health/ready
   # {"status":"ready","service":"backend","dependencies":{"database":"healthy","redis":"healthy"}}
   
   # Metrics
   curl -s https://attendance.university.edu/health/metrics
   ```

---

## 5. Automated Backup & Disaster Recovery Runbook

1. **Daily Backup Execution**:
   ```bash
   python3 scripts/backup_db.py --backup-dir /var/backups/attendance
   ```

2. **Verify Backup & Integrity Checksum**:
   ```bash
   ls -lh /var/backups/attendance/
   sha256sum -c /var/backups/attendance/attendance_backup_*.sql.gz.sha256
   ```

3. **Restoration Procedure**:
   ```bash
   # In emergency restoration:
   python3 scripts/restore_db.py /var/backups/attendance/attendance_backup_<TIMESTAMP>.sql.gz
   ```

---

## 6. Controlled Upgrade & Rollback Procedures (Maintenance Window)

> [!NOTE]
> Database schema updates and rollbacks (`alembic downgrade -1`) with container restarts are executed as a controlled procedure within a scheduled maintenance window. Active zero-downtime blue/green deployment is not currently claimed.

### Upgrade Workflow:
1. Pull new release tag:
   ```bash
   git fetch --tags && git checkout v1.0.0
   ```
2. Build new production images:
   ```bash
   docker compose -f docker-compose.prod.yml build
   ```
3. Run migrations:
   ```bash
   docker compose -f docker-compose.prod.yml run --rm backend alembic -c backend/migrations/alembic.ini upgrade head
   ```
4. Restart application services gracefully:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --no-deps backend web celery_worker
   ```

### Controlled Rollback Workflow:
1. If database schema was migrated forward:
   ```bash
   docker compose -f docker-compose.prod.yml run --rm backend alembic -c backend/migrations/alembic.ini downgrade -1
   ```
2. Checkout previous known-good tag:
   ```bash
   git checkout <PREVIOUS_STABLE_TAG>
   docker compose -f docker-compose.prod.yml up -d
   ```
