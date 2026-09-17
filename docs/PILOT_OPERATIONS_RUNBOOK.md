# Pilot Operations Runbook

**Document ID:** `PILOT_OPERATIONS_RUNBOOK`  
**System:** Digital Student Attendance System  
**Target Milestone:** Milestone 19 — University Pilot & Acceptance  
**Audience:** Campus IT Administrators, Pilot Coordinators, Faculty Tech Leads  

---

## 1. Daily Campus Service Startup & Verification

1. **Start Campus Services**:
   ```bash
   cd /opt/attendance-system
   docker compose -f docker-compose.prod.yml up -d
   ```

2. **Verify Health Probes**:
   ```bash
   curl -s http://127.0.0.1:8000/health/ready | jq .
   # Verify: database == "healthy", redis == "healthy"
   ```

3. **Verify Campus LAN & DNS**:
   - Verify campus Wi-Fi APs correctly resolve `attendance.university.edu` to the internal server IP (or reverse proxy).
   - Ensure campus subnets configured in `CAMPUS_TRUSTED_SUBNETS` match active Wi-Fi ranges (`192.168.0.0/16,10.0.0.0/8`).

4. **Verify TLS Certificate**:
   ```bash
   openssl s_client -connect attendance.university.edu:443 -servername attendance.university.edu </dev/null 2>/dev/null | openssl x509 -noout -dates
   ```

5. **Verify Background Celery Worker**:
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail=50 celery_worker
   # Verify worker reports: [Ready: celery@...]
   ```

---

## 2. Pre-Lecture Operations Checklist

- **Classroom Bluetooth Broadcasters**: Confirm classroom BLE beacon / broadcaster device is powered on and advertising UUID `0000fee0-0000-1000-8000-00805f9b34fb`.
- **Lecturer Console**: Confirm lecturer can log in at `https://attendance.university.edu/lecturer` and select today's scheduled class occurrence.
- **Dynamic QR Display**: Confirm rotating dynamic QR codes cycle smoothly every 20-30 seconds on the projector screen.

---

## 3. Emergency Offline Behavior Procedure

If campus internet or server connectivity drops during a live session:
1. **Instruct Lecturer to Switch to Offline Mode**:
   - The mobile application prompts the instructor to generate an offline session permit.
   - Instruct students to continue scanning the offline dynamic QR code.
2. **Student Local Claims**:
   - Student mobile devices store attendance evidence in local SQLite outbox (`SqliteOfflineStorage`).
   - The mobile UI displays "Saved for Synchronization".
3. **Post-Incident Reconciliation**:
   - When network connectivity is restored, students tap "Synchronize Outbox".
   - Server processes queued claims transactionally, validating cryptographic permits and granting verified credits without duplication.

---

## 4. End-of-Day Shutdown & Backup Procedure

1. **Trigger Automated Database Backup**:
   ```bash
   python3 scripts/backup_db.py
   ```
2. **Check Backup Integrity**:
   ```bash
   ls -ltr backups/
   ```
3. **Orderly Service Shutdown (if needed for server maintenance)**:
   ```bash
   docker compose -f docker-compose.prod.yml stop
   ```
