# Android Cloud Build Workflow & Physical Testing Guide

## 1. Why This Workflow Exists

Compiling Flutter mobile applications for Android requires executing the full Gradle build lifecycle, compiling Kotlin/Java source files, resolving native Android dependencies, and executing Android AAPT2 resource bundling. On resource-constrained or low-end development PCs, this process causes heavy CPU spikes, RAM exhaustion, and potential compiler crashes (such as JVM memory allocation errors).

To keep local development fast, responsive, and lightweight:
- **All heavy compilation runs in GitHub Actions runners** (Java 17, Flutter stable, Gradle daemon caching, Android compilation, AAPT2 packaging, and mobile tests).
- **The local PC only edits code, pushes branches, downloads the compiled APK artifact, and installs it via USB using ADB**.
- Local machines are **never** required to run `flutter build apk` during normal testing cycles.

```
+-------------------------------------------------------------------------+
|                              LOCAL MACHINE                              |
|                                                                         |
|   1. Edit Dart code                                                     |
|   2. Commit & push branch ------------------------------------+         |
|   7. Download compiled APK artifact <-------------------+     |         |
|   8. `adb install -r <apk>` over USB                    |     |         |
|   9. Test on physical Android device                    |     |         |
+---------------------------------------------------------|-----|---------+
                                                          |     |
                                                          |     |
+---------------------------------------------------------v-----|---------+
|                          GITHUB ACTIONS (CLOUD)               |         |
|                                                               |         |
|   3. Java 17 + Flutter Stable setup                           |         |
|   4. Gradle dependency resolution & cache lookup              |         |
|   5. `dart format`, `flutter analyze`, `flutter test`         |         |
|   6. Compile Debug APK (`android-arm64` or universal) --------+         |
+-------------------------------------------------------------------------+
```

---

## 2. Architecture & Build Options

The workflow supports two target architectures via the `apk_type` workflow parameter:

| Option | Command | When to Use | Bandwidth & Size |
| :--- | :--- | :--- | :--- |
| **`arm64`** *(Default)* | `flutter build apk --debug --target-platform android-arm64` | Modern physical Android devices (Samsung, Pixel, Xiaomi, etc.) | **Smallest size (~30–45MB)**, fastest download |
| **`universal`** | `flutter build apk --debug` | Older 32-bit devices, emulators, or unknown architectures | Larger size (~60–80MB, bundles arm64, armeabi-v7a, x86_64) |

---

## 3. How to Trigger via GitHub Web UI

1. Navigate to the repository on GitHub:  
   `https://github.com/ihsanlemar-blip/UniversityAttendaceSystem`
2. Click the **Actions** tab in the top navigation bar.
3. In the left sidebar under *Workflows*, select **Build Android APK**.
4. Click the **Run workflow** dropdown on the right:
   - **Branch**: Select the active branch (e.g. `feature/cloud-android-apk-build`).
   - **Target architecture**: Choose `arm64` (recommended) or `universal`.
5. Click **Run workflow**.
6. When the job completes (~3–5 minutes):
   - Scroll down to the **Artifacts** section of the run summary.
   - Click to download the artifact (e.g. `university-attendance-debug-arm64-<short_sha>.zip`).
   - Extract the `.apk` file from the downloaded archive.

---

## 4. How to Trigger from Windows (PowerShell Automation Script)

The repository provides an automated PowerShell script at `scripts/mobile-cloud-build.ps1` that orchestrates the entire cloud build loop directly from your Windows command line.

### Prerequisites on Windows:
- **Git** (`git --version`)
- **GitHub CLI** (`gh --version`):
  - Install via: `winget install --id GitHub.cli` or from [cli.github.com](https://cli.github.com).
  - Authenticate once: `gh auth login`.
- **Android Platform Tools** (`adb version`):
  - Pre-installed at `C:\platform-tools\adb.exe` or available via Android SDK.

### Usage Examples:

```powershell
# 1. Standard ARM64 Cloud Build (pushes branch, triggers workflow, watches progress, downloads APK)
.\scripts\mobile-cloud-build.ps1

# 2. Cloud Build + Automatic USB Installation to connected phone
.\scripts\mobile-cloud-build.ps1 -Install

# 3. Universal Fallback Cloud Build + Automatic USB Installation
.\scripts\mobile-cloud-build.ps1 -Universal -Install

# 4. Trigger build without re-pushing branch (if already pushed)
.\scripts\mobile-cloud-build.ps1 -SkipPush
```

---

## 5. Manual Installation via ADB (Over USB)

Once an APK is downloaded locally into `artifacts/android/`, you can install it manually at any time without an active Internet connection:

```powershell
# 1. Verify your Android device is connected and authorized
adb devices

# Expected output:
# List of devices attached
# R58M123456X    device

# 2. Install the debug APK with replacement flag (-r preserves application data)
adb install -r .\artifacts\android\university-attendance-debug-arm64-<sha>\UniversityAttendance-debug-arm64-<sha>.apk
```

### Device Connection Troubleshooting:
- If `adb devices` shows `unauthorized`: Check your phone's screen and tap **"Always allow from this computer"**.
- If `adb devices` shows empty:
  1. Open phone **Settings** -> **About Phone**.
  2. Tap **Build Number** 7 times to enable Developer Options.
  3. Open **Settings** -> **Developer Options** and enable **USB Debugging**.
  4. Disconnect and reconnect the USB cable.

---

## 6. Gradle Caching Strategy

The GitHub Actions workflow uses `actions/cache@v4` with cache keys derived from the project's Android build configuration:

```yaml
- name: Cache Gradle
  uses: actions/cache@v4
  with:
    path: |
      ~/.gradle/caches
      ~/.gradle/wrapper
    key: ${{ runner.os }}-gradle-${{ hashFiles('apps/mobile/android/**/*.gradle*', 'apps/mobile/android/**/gradle-wrapper.properties') }}
    restore-keys: |
      ${{ runner.os }}-gradle-
```

- **Cached Paths**: `~/.gradle/caches` and `~/.gradle/wrapper`.
- **Key Invalidation**: Any change to `build.gradle.kts`, `settings.gradle.kts`, or `gradle-wrapper.properties` creates a fresh cache entry.
- **Restore Fallback**: Prefix match `${{ runner.os }}-gradle-` ensures subsequent runs avoid re-downloading standard Android Gradle dependencies.

---

## 7. Security and Production Boundaries

> [!CAUTION]
> **Strict Security Notice:**
> - This workflow produces **DEBUG test APKs only**.
> - It does **NOT** configure Android release signing, keystores, or production certificates.
> - No secrets, keystores, or passwords are stored in the workflow or repository.
> - The generated `.sha256` checksum is for **local download integrity verification only** and does not constitute Android code signing.
> - Milestone 20 will handle official release signing, release keystores, and production distribution separately.
