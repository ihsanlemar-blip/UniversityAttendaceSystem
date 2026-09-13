# Digital Student Attendance System
## Environment Configuration Specification

**Document Version:** 1.0  
**Status:** Approved Configuration Standard  
**Milestone:** 3 — Repository & Implementation Blueprint  

---

## 1. Configuration Architecture

The Digital Student Attendance System uses environment-based configuration following the Twelve-Factor App methodology. Configuration parameters are injected via environment variables and loaded into strongly-typed Pydantic settings models (`backend/app/core/config.py`), Next.js runtime configurations, and Flutter compile-time/runtime environment declarations.

### Security Invariant
> [!CAUTION]
> Real production secrets, private keys, database passwords, and JWT signing keys must **NEVER** be committed to version control or hardcoded in documentation. Only placeholder patterns and safe local development defaults are specified here.

---

## 2. Environment Matrix

The system recognizes three deployment targets:
- `development`: Local developer workstation (Docker Compose, hot reloading enabled, relaxed CORS for local ports).
- `staging`: Campus rehearsal server (production-like containerization, realistic network latency, sanitized staging data).
- `production`: Local university campus operational server (hardened TLS, strict CORS, encrypted volumes, automated WAL archiving).

---

## 3. Environment Variable Categories

### 3.1 APP — General Application Settings
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | String | `development` | Environment mode: `development`, `staging`, `production`. |
| `APP_NAME` | String | `University Attendance System` | Application display name. |
| `APP_VERSION` | String | `0.1.0` | Semantic release version. |
| `UNIVERSITY_ID` | UUID | `00000000-0000-0000-0000-000000000001` | Default operational university entity ID. |
| `UNIVERSITY_NAME` | String | `Kabul University` | Default university institution name. |
| `UNIVERSITY_TIMEZONE` | String | `Asia/Kabul` | Local university timezone (ADR-019). Timestamps stored in UTC. |
| `DEFAULT_LOCALE` | String | `en` | Fallback language: `en` (English), `fa` (Dari), `ps` (Pashto). |

### 3.2 DATABASE — PostgreSQL Settings
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_HOST` | String | `postgres` | Database hostname or container name. |
| `DATABASE_PORT` | Integer | `5432` | Database TCP port. |
| `DATABASE_NAME` | String | `attendance_db` | Primary PostgreSQL database name. |
| `DATABASE_USER` | String | `attendance_user` | Database connection role. |
| `DATABASE_PASSWORD` | String | `dev_insecure_password` | Database user password. |
| `DATABASE_POOL_SIZE` | Integer | `20` | SQLAlchemy connection pool size. |
| `DATABASE_MAX_OVERFLOW` | Integer | `10` | SQLAlchemy max overflow connections beyond pool. |
| `DATABASE_SSL_MODE` | String | `prefer` | SSL mode: `disable` (dev), `require` (production). |

### 3.3 REDIS — Cache & Broker Settings
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `REDIS_URL` | String | `redis://redis:6379/0` | Primary Redis connection URI for caching and state. |
| `CELERY_BROKER_URL` | String | `redis://redis:6379/1` | Celery task queue broker connection URI. |
| `CELERY_RESULT_BACKEND` | String | `redis://redis:6379/2` | Celery asynchronous task result backend. |

### 3.4 AUTH — Authentication & Tokens
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `AUTH_SECRET_KEY` | String | `dev_insecure_secret_key_change_in_production` | Symmetric secret for signing access tokens (HS256). |
| `AUTH_ACCESS_TOKEN_MINUTES` | Integer | `15` | Lifetime of short-lived JWT access tokens. |
| `AUTH_REFRESH_TOKEN_DAYS` | Integer | `7` | Lifetime of rotating refresh tokens. |
| `AUTH_PASSWORD_HASH_ALGO` | String | `argon2id` | Password hashing algorithm (Argon2id). |
| `AUTH_MAX_LOGIN_ATTEMPTS` | Integer | `5` | Maximum failed attempts before temporary account lockout. |

### 3.5 ATTENDANCE — Core Attendance Rules
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `ATTENDANCE_TOKEN_ROTATION_SECONDS` | Integer | `30` | Dynamic QR HMAC rotation window (ADR-010). |
| `ATTENDANCE_TOKEN_TOLERANCE_STEPS` | Integer | `1` | Allowed drift window tolerance (±1 step). |
| `ATTENDANCE_DEFAULT_CHECKPOINT_SECONDS` | Integer | `300` | Default active duration for checkpoints (5 minutes). |
| `ATTENDANCE_LATE_THRESHOLD_MINUTES` | Integer | `10` | Minutes after class start when check-in marks "LATE". |
| `ATTENDANCE_MINIMUM_PERCENTAGE` | Float | `75.0` | University policy minimum attendance threshold. |
| `ATTENDANCE_TOKEN_HMAC_SECRET` | String | `dev_qr_hmac_secret_key_placeholder` | Secret key used to sign rotating dynamic tokens. |

### 3.6 NETWORK — Campus Network Verification
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `CAMPUS_TRUSTED_SUBNETS` | String | `192.168.0.0/16,10.0.0.0/8` | Comma-separated CIDR blocks of campus Wi-Fi networks. |
| `CAMPUS_NETWORK_CHECK_ENABLED`| Boolean | `true` | Whether to evaluate student IP against campus subnets. |

### 3.7 CLOUD SYNC — Transactional Replication
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `CLOUD_SYNC_ENABLED` | Boolean | `false` | Whether background cloud sync is activated (ADR-002). |
| `CLOUD_SYNC_ENDPOINT_URL` | String | `https://cloud.university.edu/api/v1/sync` | Cloud DR ingestion endpoint. |
| `CLOUD_SYNC_API_KEY` | String | `placeholder_cloud_sync_api_key` | Secret key authenticating campus server to cloud. |
| `CLOUD_SYNC_BATCH_SIZE` | Integer | `100` | Maximum outbox records sent per synchronization batch. |

### 3.8 BACKUP — Campus Automated Backup
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `BACKUP_ENABLED` | Boolean | `true` | Automated daily database dump flag. |
| `BACKUP_STORAGE_PATH` | String | `/var/backups/attendance` | Storage directory for database backup archives. |
| `BACKUP_RETENTION_DAYS` | Integer | `30` | Days to retain rolling backup archives before pruning. |

### 3.9 LOGGING — System Observability
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `LOG_LEVEL` | String | `INFO` | Output log severity: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `LOG_FORMAT` | String | `json` | Log formatting: `json` (production), `text` (local dev). |

### 3.10 SECURITY — Hardening & Limits
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `SECURITY_RATE_LIMIT_LOGIN` | String | `5/minute` | Rate limit for `/auth/login` per IP. |
| `SECURITY_RATE_LIMIT_CHECKIN` | String | `30/minute` | Rate limit for `/attendance/check-in` per IP. |
| `SECURITY_RATE_LIMIT_GLOBAL` | String | `300/minute` | Default global API rate limit. |

### 3.11 CORS — Cross-Origin Resource Sharing
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `CORS_ALLOWED_ORIGINS` | String | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated list of allowed web client origins. |

### 3.12 WEB — Next.js Client Configuration
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | String | `http://localhost:8000/api/v1` | Public API endpoint for browser fetch requests. |
| `NEXT_PUBLIC_APP_NAME` | String | `University Attendance Portal` | Web application display title. |
| `NEXT_PUBLIC_DEFAULT_LOCALE` | String | `en` | Initial locale for web UI. |

### 3.13 MOBILE — Flutter Client Configuration
| Variable | Type | Default (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `APP_API_BASE_URL` | String | `http://10.0.2.2:8000/api/v1` | Backend URL (10.0.2.2 for Android emulator). |
| `APP_BLE_SERVICE_UUID` | String | `0000fee0-0000-1000-8000-00805f9b34fb` | BLE service UUID for campus presence beacon. |
