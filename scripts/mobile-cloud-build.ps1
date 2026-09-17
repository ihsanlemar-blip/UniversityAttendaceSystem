<#
.SYNOPSIS
    Automates cloud-based Android debug APK compilation on GitHub Actions for local physical device testing.

.DESCRIPTION
    Offloads expensive Flutter + Gradle Android compilation from a local Windows PC to GitHub Actions.
    Pushes the active branch, dispatches the 'android-apk.yml' workflow, streams build logs,
    downloads the generated APK artifact to artifacts/android/, computes its SHA-256 checksum,
    and optionally installs the APK directly to a connected USB Android device via ADB.

.PARAMETER Arm64
    Builds ARM64 debug APK (default, optimized for modern physical Android/Samsung phones).

.PARAMETER Universal
    Builds universal multi-architecture debug APK fallback.

.PARAMETER Install
    Automatically verifies connected ADB device and installs the downloaded APK.

.PARAMETER SkipPush
    Skips pushing git branch before dispatching workflow (useful if branch is already up to date).

.EXAMPLE
    .\scripts\mobile-cloud-build.ps1
    Builds arm64 debug APK in GitHub Actions and downloads it locally.

.EXAMPLE
    .\scripts\mobile-cloud-build.ps1 -Install
    Builds arm64 debug APK, downloads it, and installs it onto connected physical phone.

.EXAMPLE
    .\scripts\mobile-cloud-build.ps1 -Universal -Install
    Builds universal debug APK and installs it.
#>

[CmdletBinding()]
param(
    [Parameter()][switch]$Arm64,
    [Parameter()][switch]$Universal,
    [Parameter()][switch]$Install,
    [Parameter()][switch]$SkipPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# 1. Determine Repository Root and Current Git Branch
try {
    $repoRoot = (git rev-parse --show-toplevel 2>$null).Trim()
} catch {
    Write-Error "Failed to determine git repository root. Please run this script within the repository."
    exit 1
}

$branch = (git branch --show-current 2>$null).Trim()
if (-not $branch) {
    Write-Error "Could not determine current Git branch. Please ensure you are in a valid Git branch."
    exit 1
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "       UNIVERSITY ATTENDANCE SYSTEM - ANDROID CLOUD BUILD       " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Repository Root: $repoRoot"
Write-Host "Current Branch:  $branch"

# 2. Check for Uncommitted Changes
$gitStatus = (git status --porcelain 2>$null)
if ($gitStatus) {
    Write-Host ""
    Write-Host "[!] Uncommitted changes detected in working tree:" -ForegroundColor Yellow
    git status --short
    Write-Host ""
    Write-Host "GitHub Actions builds code directly from the remote Git repository." -ForegroundColor Yellow
    Write-Host "Please commit or stash your changes before triggering a cloud build:" -ForegroundColor Yellow
    Write-Host "  git add . && git commit -m `"your message`"" -ForegroundColor Yellow
    Write-Host "  - OR -" -ForegroundColor Yellow
    Write-Host "  git stash push -m `"WIP`"" -ForegroundColor Yellow
    Write-Error "Working directory is not clean. Aborting cloud build."
    exit 1
}

# 3. Verify Prerequisites (GitHub CLI and ADB)
$ghCmd = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghCmd) {
    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor Red
    Write-Host "ERROR: GitHub CLI ('gh') is required but was not found on PATH." -ForegroundColor Red
    Write-Host "=================================================================" -ForegroundColor Red
    Write-Host "To install GitHub CLI on Windows:" -ForegroundColor Cyan
    Write-Host "  winget install --id GitHub.cli" -ForegroundColor White
    Write-Host "  - OR - download the Windows installer from: https://cli.github.com" -ForegroundColor White
    Write-Host "After installation, restart your terminal and authenticate:" -ForegroundColor Cyan
    Write-Host "  gh auth login" -ForegroundColor White
    Write-Host "=================================================================" -ForegroundColor Red
    exit 1
}

$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adbCmd) {
    Write-Host "[!] Android Debug Bridge ('adb') was not found on PATH." -ForegroundColor Yellow
    Write-Host "    Download Android platform-tools from: https://developer.android.com/tools/releases/platform-tools" -ForegroundColor Yellow
    Write-Host "    Add platform-tools directory to your PATH for automatic APK installation." -ForegroundColor Yellow
}

# 4. Determine Target Architecture
$apkType = "arm64"
if ($Universal) {
    $apkType = "universal"
}

Write-Host "Target Arch:     $apkType" -ForegroundColor White
Write-Host "Build Type:      debug" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan

# 5. Push Branch to Origin
if (-not $SkipPush) {
    Write-Host "[+] Pushing branch '$branch' to remote 'origin'..." -ForegroundColor Cyan
    git push -u origin $branch
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to push branch '$branch' to origin. Please verify your Git credentials."
        exit 1
    }
} else {
    Write-Host "[+] Skipping git push as requested (-SkipPush)." -ForegroundColor Yellow
}

# 6. Dispatch GitHub Actions Workflow
Write-Host "[+] Dispatching GitHub Actions workflow 'android-apk.yml'..." -ForegroundColor Cyan
Write-Host "    Branch:   $branch" -ForegroundColor Gray
Write-Host "    APK Type: $apkType" -ForegroundColor Gray

gh workflow run android-apk.yml --ref $branch -f apk_type=$apkType
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to trigger GitHub Actions workflow 'android-apk.yml'."
    exit 1
}

# 7. Locate Workflow Run
Write-Host "[+] Waiting for workflow run to register on GitHub Actions..." -ForegroundColor Cyan
$runId = $null
$runUrl = $null

for ($i = 0; $i -lt 12; $i++) {
    Start-Sleep -Seconds 3
    $runListJson = gh run list --workflow=android-apk.yml --branch=$branch --limit=1 --json databaseId,status,conclusion,url 2>$null
    if ($runListJson) {
        $runObj = $runListJson | ConvertFrom-Json
        if ($runObj -and $runObj.Count -gt 0) {
            $runId = $runObj[0].databaseId
            $runUrl = $runObj[0].url
            break
        }
    }
}

if (-not $runId) {
    Write-Error "Could not retrieve the newly triggered workflow run from GitHub. Please check https://github.com/ihsanlemar-blip/UniversityAttendaceSystem/actions"
    exit 1
}

Write-Host "[+] Located Workflow Run ID: $runId" -ForegroundColor Green
Write-Host "[+] Run URL: $runUrl" -ForegroundColor Green
Write-Host "[+] Watching workflow run progress in real time..." -ForegroundColor Cyan

# 8. Watch Workflow Execution
gh run watch $runId

# 9. Verify Run Conclusion
$finalRunJson = gh run view $runId --json status,conclusion,url | ConvertFrom-Json
if ($finalRunJson.conclusion -ne "success") {
    Write-Host ""
    Write-Host "=================================================================" -ForegroundColor Red
    Write-Host "WORKFLOW RUN FAILED or was CANCELLED." -ForegroundColor Red
    Write-Host "Run URL: $($finalRunJson.url)" -ForegroundColor Yellow
    Write-Host "=================================================================" -ForegroundColor Red
    Write-Error "Cloud APK build failed on GitHub Actions. See URL above for build logs."
    exit 1
}

Write-Host ""
Write-Host "[+] Cloud build finished successfully!" -ForegroundColor Green

# 10. Download APK Artifact
$artifactDir = Join-Path $repoRoot "artifacts\android"
if (-not (Test-Path $artifactDir)) {
    New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
}

Write-Host "[+] Downloading generated APK artifact to $artifactDir..." -ForegroundColor Cyan
gh run download $runId --dir $artifactDir
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to download artifact for run $runId."
    exit 1
}

# 11. Locate Downloaded APK File
$apkFiles = Get-ChildItem -Path $artifactDir -Filter "*.apk" -Recurse | Sort-Object LastWriteTime -Descending
if (-not $apkFiles -or $apkFiles.Count -eq 0) {
    Write-Error "No .apk file found in downloaded artifact under $artifactDir."
    exit 1
}

$apkFile = $apkFiles[0]
$fileHash = (Get-FileHash -Path $apkFile.FullName -Algorithm SHA256).Hash
$fileSizeMB = [math]::Round($apkFile.Length / 1MB, 2)

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "                 ANDROID CLOUD BUILD COMPLETE                    " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "APK Path:      $($apkFile.FullName)" -ForegroundColor White
Write-Host "File Size:     $fileSizeMB MB ($($apkFile.Length) bytes)" -ForegroundColor White
Write-Host "SHA-256:       $fileHash" -ForegroundColor White
Write-Host "Architecture:  $apkType" -ForegroundColor White
Write-Host "Workflow Run:  $runUrl" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Green

# 12. Handle Device Installation
if (-not $Install) {
    try {
        $shouldPrompt = [Environment]::UserInteractive -and -not [Console]::IsInputRedirected
    } catch {
        $shouldPrompt = $false
    }
    if ($shouldPrompt) {
        Write-Host ""
        $answer = Read-Host "Do you want to install this APK to a connected Android phone via ADB now? (y/N)"
        if ($answer -match "^[yY](es)?$") {
            $Install = $true
        }
    }
}

if ($Install) {
    Write-Host ""
    Write-Host "[+] Checking for connected Android devices via ADB..." -ForegroundColor Cyan
    if (-not $adbCmd) {
        Write-Host "[!] ADB executable not found on PATH. Cannot proceed with automatic installation." -ForegroundColor Yellow
        Write-Host "    Install platform-tools and add to PATH, then run:" -ForegroundColor Yellow
        Write-Host "    adb install -r `"$($apkFile.FullName)`"" -ForegroundColor White
        exit 0
    }

    $rawDevices = adb devices
    $authorizedDevices = @()
    foreach ($line in ($rawDevices -split "`r?`n")) {
        if ($line -match '^([^\s]+)\s+device$') {
            $authorizedDevices += $matches[1]
        }
    }

    if ($authorizedDevices.Count -gt 0) {
        Write-Host "[+] Found authorized device(s): $($authorizedDevices -join ', ')" -ForegroundColor Green
        Write-Host "[+] Installing APK onto device ($($authorizedDevices[0]))..." -ForegroundColor Cyan
        adb install -r "$($apkFile.FullName)"
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "=================================================================" -ForegroundColor Green
            Write-Host "APK SUCCESSFULLY INSTALLED ON CONNECTED PHYSICAL DEVICE!" -ForegroundColor Green
            Write-Host "=================================================================" -ForegroundColor Green
        } else {
            Write-Host "[!] ADB installation failed. Check device screen for permission prompts." -ForegroundColor Red
        }
    } else {
        Write-Host ""
        Write-Host "=================================================================" -ForegroundColor Yellow
        Write-Host "CLOUD APK BUILD COMPLETE. PHYSICAL APK INSTALLATION PENDING." -ForegroundColor Yellow
        Write-Host "=================================================================" -ForegroundColor Yellow
        Write-Host "No authorized Android device was detected by ADB." -ForegroundColor Yellow
        Write-Host "To install this APK on your physical Android phone:" -ForegroundColor Cyan
        Write-Host "  1. Connect phone to PC via USB." -ForegroundColor White
        Write-Host "  2. In phone Settings -> Developer Options -> Enable 'USB Debugging'." -ForegroundColor White
        Write-Host "  3. Accept the 'Allow USB debugging?' RSA prompt on the phone screen." -ForegroundColor White
        Write-Host "  4. Verify connection: adb devices" -ForegroundColor White
        Write-Host "  5. Install manually:" -ForegroundColor Cyan
        Write-Host "     adb install -r `"$($apkFile.FullName)`"" -ForegroundColor Green
        Write-Host "=================================================================" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Physical APK installation skipped." -ForegroundColor Yellow
    Write-Host "To install manually over USB via ADB:" -ForegroundColor Cyan
    Write-Host "  adb devices" -ForegroundColor White
    Write-Host "  adb install -r `"$($apkFile.FullName)`"" -ForegroundColor Green
}
