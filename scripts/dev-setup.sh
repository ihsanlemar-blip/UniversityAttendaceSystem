#!/usr/bin/env bash
# Developer Environment Setup Script (Linux / macOS)
set -euo pipefail

echo "============================================================"
echo "Digital Student Attendance System — Environment Setup"
echo "============================================================"

# 1. Check for .env file
if [ ! -f ".env" ]; then
    echo "[*] Creating .env from .env.example..."
    cp .env.example .env
    echo "[+] .env created successfully."
else
    echo "[i] .env file already exists."
fi

# 2. Setup Python Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[*] Creating Python virtual environment in .venv..."
    python3 -m venv .venv
    echo "[+] Virtual environment created."
else
    echo "[i] .venv virtual environment already exists."
fi

echo ""
echo "Setup completed successfully."
echo "To start development:"
echo "  source .venv/bin/activate"
echo "  pip install -r backend/requirements.txt"
echo "  uvicorn backend.app.main:app --reload --port 8000"
