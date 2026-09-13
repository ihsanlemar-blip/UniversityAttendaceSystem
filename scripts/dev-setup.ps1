# Developer Environment Setup Script (Windows PowerShell)
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Digital Student Attendance System — Environment Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "[*] Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[+] .env created successfully." -ForegroundColor Green
} else {
    Write-Host "[i] .env file already exists." -ForegroundColor Gray
}

# 2. Setup Python Virtual Environment
if (-not (Test-Path ".venv")) {
    Write-Host "[*] Creating Python virtual environment in .venv..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "[+] Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "[i] .venv virtual environment already exists." -ForegroundColor Gray
}

# 3. Inform next steps
Write-Host ""
Write-Host "Setup completed successfully." -ForegroundColor Green
Write-Host "To start development:" -ForegroundColor White
Write-Host "  1. Activate venv: .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "  2. Install dependencies: pip install -r backend/requirements.txt" -ForegroundColor Gray
Write-Host "  3. Start backend: uvicorn backend.app.main:app --reload --port 8000" -ForegroundColor Gray
Write-Host "  4. Start web: cd apps/web; npm install; npm run dev" -ForegroundColor Gray
