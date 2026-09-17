#!/usr/bin/env python3
"""Cross-platform database restore script for PostgreSQL 16.

Performs:
1. Cryptographic SHA-256 integrity checksum verification before executing restore.
2. Safe database restoration via local psql or Docker container.
"""

import argparse
import gzip
import hashlib
import os
import shutil
import subprocess
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="University Attendance System Database Restore")
    parser.add_argument("backup_file", help="Path to .sql.gz backup file")
    parser.add_argument("--db-host", default=os.getenv("DATABASE_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", default=os.getenv("DATABASE_PORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("DATABASE_NAME", "attendance_db"))
    parser.add_argument("--db-user", default=os.getenv("DATABASE_USER", "attendance_user"))
    parser.add_argument("--db-pass", default=os.getenv("DATABASE_PASSWORD", "dev_insecure_password"))
    return parser.parse_args()


def restore_database():
    args = parse_args()

    if not os.path.isfile(args.backup_file):
        print(f"[!] Error: Backup file not found: {args.backup_file}", file=sys.stderr)
        return 1

    # Verify SHA256 checksum if .sha256 file is present
    checksum_file = f"{args.backup_file}.sha256"
    if os.path.isfile(checksum_file):
        print("[+] Verifying SHA-256 backup integrity checksum...")
        with open(checksum_file, "r", encoding="utf-8") as f:
            expected_hash = f.read().split()[0].strip().lower()

        h = hashlib.sha256()
        with open(args.backup_file, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_hash = h.hexdigest().lower()

        if actual_hash != expected_hash:
            print(f"[!] CHECKSUM MISMATCH: Expected {expected_hash}, got {actual_hash}", file=sys.stderr)
            return 1
        print("[+] Checksum verified successfully.")

    print(f"[+] Restoring database from {args.backup_file}...")
    psql = shutil.which("psql")
    env = os.environ.copy()
    env["PGPASSWORD"] = args.db_pass

    if psql:
        with gzip.open(args.backup_file, "rb") as gz:
            cmd = [
                psql,
                "-h", args.db_host,
                "-p", str(args.db_port),
                "-U", args.db_user,
                "-d", args.db_name,
            ]
            res = subprocess.run(cmd, stdin=gz, env=env, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"[!] Restore failed: {res.stderr}", file=sys.stderr)
                return 1
    else:
        # Fallback to docker
        with gzip.open(args.backup_file, "rb") as gz:
            docker_cmd = [
                "docker", "exec", "-i", "attendance_postgres_prod",
                "psql", "-U", args.db_user, "-d", args.db_name
            ]
            try:
                res = subprocess.run(docker_cmd, stdin=gz, capture_output=True, text=True)
                if res.returncode != 0:
                    print(f"[!] Docker restore failed: {res.stderr}", file=sys.stderr)
                    return 1
            except Exception as e:
                print(f"[!] Restore failed: {e}", file=sys.stderr)
                return 1

    print("[+] Database restoration completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(restore_database())
