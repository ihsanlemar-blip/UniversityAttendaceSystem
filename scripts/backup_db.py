#!/usr/bin/env python3
"""Cross-platform automated database backup script for PostgreSQL 16.

Performs:
1. Automated pg_dump backup with gzip compression.
2. Cryptographic SHA-256 integrity checksum generation.
3. Retention window pruning for old backups.
"""

import argparse
import datetime
import hashlib
import os
import shutil
import subprocess
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="University Attendance System Database Backup")
    parser.add_argument("--backup-dir", default=os.getenv("BACKUP_PATH", "backups"), help="Destination directory")
    parser.add_argument("--retention-days", type=int, default=int(os.getenv("BACKUP_RETENTION_DAYS", "30")), help="Retention period in days")
    parser.add_argument("--db-host", default=os.getenv("DATABASE_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", default=os.getenv("DATABASE_PORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("DATABASE_NAME", "attendance_db"))
    parser.add_argument("--db-user", default=os.getenv("DATABASE_USER", "attendance_user"))
    parser.add_argument("--db-pass", default=os.getenv("DATABASE_PASSWORD", "dev_insecure_password"))
    return parser.parse_args()


def backup_database():
    args = parse_args()
    os.makedirs(args.backup_dir, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%SZ")
    backup_filename = f"attendance_backup_{timestamp}.sql.gz"
    backup_path = os.path.join(args.backup_dir, backup_filename)
    checksum_path = f"{backup_path}.sha256"

    print(f"[{datetime.datetime.now(datetime.UTC).isoformat()}] Starting database backup...")

    # Check if pg_dump is installed locally
    pg_dump = shutil.which("pg_dump")
    env = os.environ.copy()
    env["PGPASSWORD"] = args.db_pass

    if pg_dump:
        cmd = [
            pg_dump,
            "-h", args.db_host,
            "-p", str(args.db_port),
            "-U", args.db_user,
            "-d", args.db_name,
            "-Z", "9",
            "-f", backup_path,
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[!] pg_dump failed: {res.stderr}", file=sys.stderr)
    else:
        # Fallback: check candidate docker containers
        candidate_containers = [
            getattr(args, "container", None),
            "attendance-postgres",
            "attendance_postgres_prod",
        ]
        target_container = None
        for c in candidate_containers:
            if not c:
                continue
            check = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", c], capture_output=True, text=True)
            if check.returncode == 0 and "true" in check.stdout.lower():
                target_container = c
                break

        if not target_container:
            print("[!] Local pg_dump and Docker postgres containers unavailable.", file=sys.stderr)
            return 1

        docker_cmd = [
            "docker", "exec", target_container,
            "pg_dump", "-U", args.db_user, "-d", args.db_name, "-Z", "9"
        ]
        try:
            with open(backup_path, "wb") as f:
                res = subprocess.run(docker_cmd, stdout=f, stderr=subprocess.PIPE)
            if res.returncode != 0:
                print(f"[!] Docker backup failed: {res.stderr.decode()}", file=sys.stderr)
                return 1
        except Exception as e:
            print(f"[!] Backup failed: {e}", file=sys.stderr)
            return 1

    # Generate SHA-256 Checksum
    h = hashlib.sha256()
    with open(backup_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    digest = h.hexdigest()

    with open(checksum_path, "w", encoding="utf-8") as f:
        f.write(f"{digest}  {backup_filename}\n")

    print(f"[+] Backup completed successfully: {backup_path}")
    print(f"[+] SHA256 Checksum: {digest}")

    # Prune old backups
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=args.retention_days)
    for fname in os.listdir(args.backup_dir):
        if fname.startswith("attendance_backup_"):
            fpath = os.path.join(args.backup_dir, fname)
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
                print(f"[-] Pruned aged backup: {fname}")

    return 0


if __name__ == "__main__":
    sys.exit(backup_database())
