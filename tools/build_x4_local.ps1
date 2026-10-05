param(
    [switch]$SkipSetup,
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..")).Path
Set-Location $Root

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "Required command not found: $Name"
    }
}

Write-Host "=== CrossPoint X4 local build ===" -ForegroundColor Cyan
Write-Host "Repository: $Root"

Require-Command git

if (-not (Test-Path "platformio.ini")) {
    Fail "platformio.ini not found. Run this script from the CrossPoint repository."
}

# Extract build ID for output naming.
$buildHeader = Get-Content "src/CPHUNBuildId.h" -Raw
$m = [regex]::Match($buildHeader, '#define\s+CPHUN_BUILD_ID\s+"([^"]+)"')
if (-not $m.Success) {
    Fail "Could not read CPHUN_BUILD_ID."
}
$buildId = $m.Groups[1].Value
Write-Host "Build ID: $buildId"

# Use the already checked-out SDK when possible. This means subsequent local
# builds do not need GitHub just to refresh submodules.
$expectedSdk = "13418e0986b05039bf056e050a6df5305d47c209"
if (-not (Test-Path "freeink-sdk/.git")) {
    if ($SkipSetup) {
        Fail "freeink-sdk is missing and -SkipSetup was requested."
    }
    Write-Host "Initializing git submodules..."
    git submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) { Fail "git submodule update failed." }
}

$sdkHead = (git -C freeink-sdk rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { Fail "Cannot inspect freeink-sdk." }
if ($sdkHead -ne $expectedSdk) {
    if ($SkipSetup) {
        Fail "freeink-sdk revision is $sdkHead, expected $expectedSdk."
    }
    Write-Host "Updating submodules to the pinned revision..."
    git submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) { Fail "git submodule update failed." }
    $sdkHead = (git -C freeink-sdk rev-parse HEAD).Trim()
    if ($sdkHead -ne $expectedSdk) {
        Fail "freeink-sdk revision is still $sdkHead, expected $expectedSdk."
    }
}

# Basic source audit matching the important invariants from CI.
$checks = @(
    @{ Path="src/CPHUNBuildId.h"; Text=$buildId },
    @{ Path="lib/Epub/Epub/OpticalLineCorrection.h"; Text="MAX_INK_CORRECTION_PX = 8;" },
    @{ Path="lib/LibraryIndex/LibraryBuilder.cpp"; Text='return FsHelpers::checkFileExtension(name, ".epub");' },
    @{ Path="src/activities/home/CoverGridBrowserActivity.cpp"; Text="buildReadingShelves()" },
    @{ Path="src/activities/home/CoverGridBrowserActivity.cpp"; Text='{"Legutóbbi", "Újdonságok", "Címek", "Szerzők"}' },
    @{ Path="src/components/themes/BaseTheme.cpp"; Text="renderer.getScreenWidth() - bookmarkStatusIconWidth - 2" }
)
foreach ($c in $checks) {
    if (-not (Select-String -Path $c.Path -SimpleMatch $c.Text -Quiet)) {
        Fail "Source audit failed: '$($c.Text)' not found in $($c.Path)"
    }
}
Write-Host "Source audit: OK" -ForegroundColor Green

# Optional host regression tests. These need CMake + Ninja installed.
if ($RunTests) {
    Require-Command cmake
    Require-Command ninja
    Write-Host "Configuring regression tests..."
    cmake -S test -B build/test -G Ninja -DCMAKE_BUILD_TYPE=Release
    if ($LASTEXITCODE -ne 0) { Fail "CMake configure failed." }
    cmake --build build/test -j2
    if ($LASTEXITCODE -ne 0) { Fail "Regression test build failed." }
    ctest --test-dir build/test --output-on-failure -j2
    if ($LASTEXITCODE -ne 0) { Fail "Regression tests failed." }
}

$venv = Join-Path $Root ".venv-local"
$pio = Join-Path $venv "Scripts\pio.exe"
$pythonExe = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $pio)) {
    if ($SkipSetup) {
        Fail "Local PlatformIO environment is missing: $pio"
    }

    $launcher = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $launcher = "py"
        Write-Host "Creating local Python environment with py..."
        & py -3 -m venv $venv
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $launcher = "python"
        Write-Host "Creating local Python environment with python..."
        & python -m venv $venv
    } else {
        Fail "Python 3 not found. Install Python 3, then run again."
    }
    if ($LASTEXITCODE -ne 0) { Fail "Could not create Python virtual environment." }

    Write-Host "Installing the same PlatformIO core used by GitHub Actions..."
    & $pythonExe -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Fail "pip upgrade failed." }

    & $pythonExe -m pip install -U "https://github.com/pioarduino/platformio-core/archive/refs/tags/v6.1.19.zip" "littlefs-python>=0.16.0" "fatfs-ng>=0.1.14"
    if ($LASTEXITCODE -ne 0) {
        Fail "PlatformIO dependency installation failed. First-time setup needs Internet/GitHub access."
    }
}

if (-not (Test-Path $pio)) {
    Fail "pio.exe was not created in the local environment."
}

# Track only the same source areas that CI protects.
$before = git diff -- src lib vendor platformio.ini .gitmodules
if ($LASTEXITCODE -ne 0) { Fail "git diff failed." }

Write-Host ""
Write-Host "Building X4 (PlatformIO environment: default)..." -ForegroundColor Cyan
& $pio run -e default
if ($LASTEXITCODE -ne 0) { Fail "PlatformIO X4 build failed." }

$firmware = Join-Path $Root ".pio\build\default\firmware.bin"
if (-not (Test-Path $firmware)) {
    Fail "Build completed but firmware.bin was not found."
}

$after = git diff -- src lib vendor platformio.ini .gitmodules
if ($LASTEXITCODE -ne 0) { Fail "git diff failed after build." }
if (($before -join "`n") -ne ($after -join "`n")) {
    Fail "Tracked source changed during the build."
}

$outDir = Join-Path $Root "build-output"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$outFile = Join-Path $outDir ("firmware-X4-" + $buildId + ".bin")
Copy-Item -Force $firmware $outFile
Copy-Item -Force $firmware (Join-Path $outDir "firmware.bin")

$bytes = (Get-Item $outFile).Length
Write-Host ""
Write-Host "BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "Firmware: $outFile"
Write-Host "Bytes: $bytes"
Write-Host ""
Write-Host "For later offline-ish builds, keep .venv-local and the PlatformIO package cache."
