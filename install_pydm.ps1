#Requires -Version 5.1
<#
.SYNOPSIS
    PyDM - Download Manager — Production Installer for Windows.

.DESCRIPTION
    Installs PyDM and its dependencies on Windows.
    Can be run directly or piped from a URL:
      irm https://raw.githubusercontent.com/happy-fox-devs/pydm/main/install_pydm.ps1 | iex

.PARAMETER Update
    Force update mode (skip dependency installation).
#>

param(
    [switch]$Update
)

$ErrorActionPreference = "Stop"

# ─── Configuration ───────────────────────────────────────────────────────────

$INSTALL_DIR = Join-Path $env:LOCALAPPDATA "pydm"
$BIN_DIR = Join-Path $INSTALL_DIR "bin"
$REPO_URL = "https://github.com/happy-fox-devs/pydm.git"

$ARIA2_VERSION = "1.37.0"
$ARIA2_URL = "https://github.com/aria2/aria2/releases/download/release-$ARIA2_VERSION/aria2-$ARIA2_VERSION-win-64bit-build1.zip"

$FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# ─── Helpers ─────────────────────────────────────────────────────────────────

function Write-Banner {
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host "             PyDM - Download Manager" -ForegroundColor Cyan
    Write-Host "             Windows Installer" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Step, [string]$Message)
    Write-Host ""
    Write-Host "[$Step] $Message" -ForegroundColor Blue
}

# ─── Detect update mode ─────────────────────────────────────────────────────

$IsUpdate = $Update.IsPresent
if (-not $IsUpdate -and (Test-Path (Join-Path $INSTALL_DIR "pydm\main.py"))) {
    $IsUpdate = $true
}

Write-Banner
if ($IsUpdate) {
    Write-Host "               (Update Mode Detected)" -ForegroundColor Cyan
}
Write-Host "==================================================" -ForegroundColor Cyan

# ─── Step 1: Dependencies ───────────────────────────────────────────────────

if (-not $IsUpdate) {
    Write-Step "1/5" "Checking dependencies (aria2, ffmpeg)..."

    # --- aria2c ---
    $systemAria2 = Get-Command aria2c -ErrorAction SilentlyContinue
    if ($systemAria2) {
        Write-Host "  [OK] aria2c found in PATH: $($systemAria2.Source)" -ForegroundColor Green
    }
    else {
        New-Item -ItemType Directory -Path $BIN_DIR -Force | Out-Null
        $aria2Exe = Join-Path $BIN_DIR "aria2c.exe"
        if (-not (Test-Path $aria2Exe)) {
            Write-Host "  aria2c not found in PATH. Downloading v$ARIA2_VERSION..."
            $aria2Zip = Join-Path $env:TEMP "aria2.zip"
            Invoke-WebRequest -Uri $ARIA2_URL -OutFile $aria2Zip -UseBasicParsing
            $aria2Extract = Join-Path $env:TEMP "aria2_extract"
            Expand-Archive -Path $aria2Zip -DestinationPath $aria2Extract -Force
            $found = Get-ChildItem -Path $aria2Extract -Recurse -Filter "aria2c.exe" | Select-Object -First 1
            if ($found) {
                Copy-Item $found.FullName $aria2Exe -Force
                Write-Host "  [OK] aria2c installed to $aria2Exe" -ForegroundColor Green
            }
            else {
                Write-Host "  [ERROR] Could not find aria2c.exe in the archive" -ForegroundColor Red
            }
            Remove-Item $aria2Zip -Force -ErrorAction SilentlyContinue
            Remove-Item $aria2Extract -Recurse -Force -ErrorAction SilentlyContinue
        }
        else {
            Write-Host "  [OK] aria2c already in local bin" -ForegroundColor Green
        }
    }

    # --- ffmpeg ---
    $systemFfmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($systemFfmpeg) {
        Write-Host "  [OK] ffmpeg found in PATH: $($systemFfmpeg.Source)" -ForegroundColor Green
    }
    else {
        New-Item -ItemType Directory -Path $BIN_DIR -Force | Out-Null
        $ffmpegExe = Join-Path $BIN_DIR "ffmpeg.exe"
        if (-not (Test-Path $ffmpegExe)) {
            Write-Host "  ffmpeg not found in PATH. Downloading (this may take a moment)..."
            $ffmpegZip = Join-Path $env:TEMP "ffmpeg.zip"
            Invoke-WebRequest -Uri $FFMPEG_URL -OutFile $ffmpegZip -UseBasicParsing
            $ffmpegExtract = Join-Path $env:TEMP "ffmpeg_extract"
            Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegExtract -Force
            $found = Get-ChildItem -Path $ffmpegExtract -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
            if ($found) {
                Copy-Item $found.FullName $ffmpegExe -Force
                $probe = Get-ChildItem -Path $ffmpegExtract -Recurse -Filter "ffprobe.exe" | Select-Object -First 1
                if ($probe) { Copy-Item $probe.FullName (Join-Path $BIN_DIR "ffprobe.exe") -Force }
                Write-Host "  [OK] ffmpeg installed to $ffmpegExe" -ForegroundColor Green
            }
            else {
                Write-Host "  [ERROR] Could not find ffmpeg.exe in the archive" -ForegroundColor Red
            }
            Remove-Item $ffmpegZip -Force -ErrorAction SilentlyContinue
            Remove-Item $ffmpegExtract -Recurse -Force -ErrorAction SilentlyContinue
        }
        else {
            Write-Host "  [OK] ffmpeg already in local bin" -ForegroundColor Green
        }
    }

    # Add bin dir to user PATH only if we created it
    if (Test-Path $BIN_DIR) {
        $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        if ($userPath -notlike "*$BIN_DIR*") {
            [Environment]::SetEnvironmentVariable("PATH", "$BIN_DIR;$userPath", "User")
            $env:PATH = "$BIN_DIR;$env:PATH"
            Write-Host "  [OK] Added $BIN_DIR to user PATH" -ForegroundColor Green
        }
    }
}
else {
    Write-Step "1/5" "Skipping dependencies (Update Mode)..."
}

# ─── Step 2: Deploy PyDM ────────────────────────────────────────────────────

Write-Step "2/5" "Deploying PyDM to $INSTALL_DIR..."
New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null

# Check if we're running from within the project source
if (Test-Path (Join-Path $PSScriptRoot "pydm\main.py")) {
    Write-Host "  Copying local files..."
    $source = $PSScriptRoot
    # Copy everything except .git and venv
    Get-ChildItem -Path $source -Exclude @(".git", "venv", ".venv", "__pycache__", "dist") | ForEach-Object {
        Copy-Item $_.FullName -Destination $INSTALL_DIR -Recurse -Force
    }
}
else {
    Write-Host "  Fetching from Git repository..."
    if (Test-Path (Join-Path $INSTALL_DIR ".git")) {
        Push-Location $INSTALL_DIR
        git pull origin main
        Pop-Location
    }
    else {
        git clone $REPO_URL $INSTALL_DIR
    }
}

# ─── Step 3: Python venv ────────────────────────────────────────────────────

Write-Step "3/5" "Setting up isolated Python environment..."

# Find a working Python interpreter (mise, py launcher, python3, python)
function Find-SystemPython {
    # 1. Try mise (if the project uses it)
    $mise = Get-Command mise -ErrorAction SilentlyContinue
    if ($mise) {
        try {
            $misePython = & mise which python 2>$null
            if ($misePython -and (Test-Path $misePython)) { return $misePython }
        } catch {}
    }
    # 2. Try py launcher (standard Windows Python launcher)
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }
    # 3. Try python3
    $python3 = Get-Command python3 -ErrorAction SilentlyContinue
    if ($python3 -and $python3.Source -notlike "*WindowsApps*") { return $python3.Source }
    # 4. Try python (skip Microsoft Store stub)
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python -and $python.Source -notlike "*WindowsApps*") { return $python.Source }
    return $null
}

$systemPython = Find-SystemPython
if (-not $systemPython) {
    Write-Host "  [ERROR] Python not found! Install Python from https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "  Using Python: $systemPython"

Push-Location $INSTALL_DIR

$venvDir = Join-Path $INSTALL_DIR "venv"
if (-not (Test-Path $venvDir)) {
    if ($systemPython -match 'py(\.exe)?$') {
        & $systemPython -3 -m venv venv
    } else {
        & $systemPython -m venv venv
    }
}

$pipExe = Join-Path $venvDir "Scripts\pip.exe"
& $pipExe install -r requirements.txt

Pop-Location

# ─── Step 4: Register Native Messaging ──────────────────────────────────────

Write-Step "4/5" "Registering Browser Native Messaging..."
$nmhScript = Join-Path $INSTALL_DIR "native_host\install.ps1"
if (Test-Path $nmhScript) {
    & powershell.exe -ExecutionPolicy Bypass -File $nmhScript -Chrome -Firefox
}
else {
    Write-Host "  [WARNING] native_host\install.ps1 not found, skipping." -ForegroundColor Yellow
}

# ─── Step 5: Build Extension ────────────────────────────────────────────────

Write-Step "5/5" "Packaging Browser Extension..."
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
& $pythonExe (Join-Path $INSTALL_DIR "scripts\build_extension.py")

$extensionZip = Join-Path $INSTALL_DIR "dist\pydm_extension.zip"
$desktopZip = Join-Path ([Environment]::GetFolderPath("Desktop")) "pydm_extension.zip"
if ((Test-Path $extensionZip) -and (Test-Path ([Environment]::GetFolderPath("Desktop")))) {
    Copy-Item $extensionZip $desktopZip -Force
    $extLocation = $desktopZip
}
else {
    $extLocation = $extensionZip
}

# ─── Create Start Menu shortcut ─────────────────────────────────────────────

$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$shortcutPath = Join-Path $startMenuDir "PyDM.lnk"

# Use pythonw.exe (no console window) for the shortcut
$pythonwExe = Join-Path $venvDir "Scripts\pythonw.exe"
if (-not (Test-Path $pythonwExe)) { $pythonwExe = $pythonExe }

try {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $pythonwExe
    $shortcut.Arguments = "-m pydm.main"
    $shortcut.WorkingDirectory = $INSTALL_DIR
    $iconPath = Join-Path $INSTALL_DIR "assets\icon.ico"
    if (Test-Path $iconPath) { $shortcut.IconLocation = $iconPath }
    $shortcut.Description = "PyDM - Python Download Manager"
    $shortcut.Save()
    Write-Host "  [OK] Start Menu shortcut created (using pythonw, no console)" -ForegroundColor Green
}
catch {
    Write-Host "  [WARNING] Could not create Start Menu shortcut: $_" -ForegroundColor Yellow
}

# ─── Done ────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
if ($IsUpdate) {
    Write-Host "       PyDM Updated Successfully!" -ForegroundColor Green
}
else {
    Write-Host "       PyDM Installed Successfully!" -ForegroundColor Green
}
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "> PyDM has been installed to: $INSTALL_DIR" -ForegroundColor White
Write-Host "> Search 'PyDM' in your Start Menu to launch it." -ForegroundColor White
Write-Host ""
Write-Host "Final Step for Browser Integration:" -ForegroundColor Yellow
Write-Host "1. Your extension package is here:"
Write-Host "   -> $extLocation"
Write-Host "2. Open chrome://extensions (or brave://extensions)"
Write-Host "3. Turn ON 'Developer mode' (Top right)"
Write-Host "4. Drag and drop the .zip file directly into the browser."
Write-Host ""
