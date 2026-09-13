#!/usr/bin/env bash
# Developer Start Services Script (Linux / macOS)
set -euo pipefail

echo "Starting local development services..."
if command -v docker &> /dev/null; then
    echo "[*] Starting PostgreSQL and Redis containers..."
    docker compose up -d postgres redis
    echo "[+] Containers running. Ready for local backend execution."
else
    echo "[!] Docker not detected. Ensure PostgreSQL and Redis are running locally."
fi
