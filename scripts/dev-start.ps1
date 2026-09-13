# Developer Start Services Script (Windows PowerShell)
Write-Host "Starting local development services..." -ForegroundColor Cyan

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "[*] Starting PostgreSQL and Redis containers..." -ForegroundColor Yellow
    docker compose up -d postgres redis
    Write-Host "[+] Containers running. Ready for local backend execution." -ForegroundColor Green
} else {
    Write-Host "[!] Docker not detected on host. Ensure PostgreSQL and Redis are running locally." -ForegroundColor Yellow
}
