#Requires -Version 5.1
<#
.SYNOPSIS
    PyDM Native Messaging Host Installer for Windows.

.DESCRIPTION
    Registers the native messaging host manifest for Chrome/Chromium/Brave and/or Firefox
    so the browser extension can communicate with the PyDM application.

.PARAMETER Chrome
    Install for Chrome, Chromium, and Brave.

.PARAMETER Firefox
    Install for Firefox.

.PARAMETER Uninstall
    Remove installed manifests and registry keys.

.EXAMPLE
    .\install.ps1 -Chrome
    .\install.ps1 -Chrome -Firefox
    .\install.ps1 -Uninstall
#>

param(
    [switch]$Chrome,
    [switch]$Firefox,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$HostName = "com.pydm.native"
$WrapperPath = Join-Path $ScriptDir "pydm_native_host.bat"

# If no flags specified, install for all
if (-not $Chrome -and -not $Firefox -and -not $Uninstall) {
    $Chrome = $true
    $Firefox = $true
}

# Registry paths
$ChromeRegPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName"
$ChromiumRegPath = "HKCU:\Software\Chromium\NativeMessagingHosts\$HostName"
$BraveRegPath = "HKCU:\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\$HostName"
$FirefoxRegPath = "HKCU:\Software\Mozilla\NativeMessagingHosts\$HostName"

function Find-Python {
    $venvPython = Join-Path $ProjectDir "venv\Scripts\python.exe"
    $dotVenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) { return $venvPython }
    elseif (Test-Path $dotVenvPython) { return $dotVenvPython }
    else { return "python" }
}

function New-ManifestJson {
    param(
        [string]$ManifestType  # "chrome" or "firefox"
    )
    $manifestPath = Join-Path $ScriptDir "${HostName}_${ManifestType}.json"
    # Escape backslashes for JSON
    $escapedWrapper = $WrapperPath -replace '\\', '\\'

    if ($ManifestType -eq "firefox") {
        $json = @"
{
  "name": "$HostName",
  "description": "PyDM Native Messaging Host",
  "path": "$escapedWrapper",
  "type": "stdio",
  "allowed_extensions": [
    "pydm@pydm.local"
  ]
}
"@
    }
    else {
        $json = @"
{
  "name": "$HostName",
  "description": "PyDM Native Messaging Host",
  "path": "$escapedWrapper",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://pflmlgjlhcahdkphbimklhjahepkknec/"
  ]
}
"@
    }

    Set-Content -Path $manifestPath -Value $json -Encoding UTF8
    return $manifestPath
}

function Install-ForRegistry {
    param(
        [string]$RegPath,
        [string]$ManifestFile,
        [string]$BrowserName
    )
    $parentPath = Split-Path -Parent $RegPath
    if (-not (Test-Path $parentPath)) {
        New-Item -Path $parentPath -Force | Out-Null
    }
    New-Item -Path $RegPath -Force | Out-Null
    Set-ItemProperty -Path $RegPath -Name "(Default)" -Value $ManifestFile
    Write-Host "[OK] Installed for ${BrowserName}: $RegPath" -ForegroundColor Green
}

function Uninstall-ForRegistry {
    param(
        [string]$RegPath,
        [string]$BrowserName
    )
    if (Test-Path $RegPath) {
        Remove-Item -Path $RegPath -Force
        Write-Host "[OK] Removed from ${BrowserName}" -ForegroundColor Yellow
    }
    else {
        Write-Host "[--] Not present in $BrowserName" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  PyDM Native Messaging Host Installer" -ForegroundColor Cyan
Write-Host "             (Windows)" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

if ($Uninstall) {
    Write-Host "Uninstalling..." -ForegroundColor Yellow
    if ($Chrome) {
        Uninstall-ForRegistry -RegPath $ChromeRegPath -BrowserName "Chrome"
        Uninstall-ForRegistry -RegPath $ChromiumRegPath -BrowserName "Chromium"
        Uninstall-ForRegistry -RegPath $BraveRegPath -BrowserName "Brave"
    }
    if ($Firefox) {
        Uninstall-ForRegistry -RegPath $FirefoxRegPath -BrowserName "Firefox"
    }
    # Clean up generated files
    Get-ChildItem -Path $ScriptDir -Filter "${HostName}_*.json" | Remove-Item -Force
    Write-Host ""
    Write-Host "[OK] Uninstallation complete" -ForegroundColor Green
}
else {
    Write-Host "Installing..." -ForegroundColor Cyan
    Write-Host "Wrapper: $WrapperPath"
    Write-Host "Python:  $(Find-Python)"
    Write-Host ""

    if ($Chrome) {
        $manifest = New-ManifestJson -ManifestType "chrome"
        Write-Host "Manifest: $manifest"
        Install-ForRegistry -RegPath $ChromeRegPath -ManifestFile $manifest -BrowserName "Chrome"
        Install-ForRegistry -RegPath $ChromiumRegPath -ManifestFile $manifest -BrowserName "Chromium"
        Install-ForRegistry -RegPath $BraveRegPath -ManifestFile $manifest -BrowserName "Brave"
    }
    if ($Firefox) {
        $manifest = New-ManifestJson -ManifestType "firefox"
        Write-Host "Manifest: $manifest"
        Install-ForRegistry -RegPath $FirefoxRegPath -ManifestFile $manifest -BrowserName "Firefox"
    }
    Write-Host ""
    Write-Host "[OK] Installation complete" -ForegroundColor Green
}
Write-Host ""
