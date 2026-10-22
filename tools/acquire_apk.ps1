param(
    [Parameter(Mandatory = $true)][string]$Serial,
    [string]$AdbPath = (Join-Path $env:LOCALAPPDATA 'Android/Sdk/platform-tools/adb.exe')
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$reaPath = Join-Path $projectRoot '_private/tooling/node_modules/rea-agents/scripts/rea.mjs'
if (!(Test-Path -LiteralPath $reaPath)) { throw 'Predisporre REA in _private/tooling come indicato in tools/README.md.' }
if (!(Test-Path -LiteralPath $AdbPath)) { throw 'Indicare il percorso di adb con -AdbPath.' }
$env:REA_ADB_PATH = (Resolve-Path -LiteralPath $AdbPath).Path
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$destination = Join-Path $projectRoot ('_private/apk/acquisition-' + $stamp)
New-Item -ItemType Directory -Path $destination | Out-Null
& node $reaPath pull-adb-package $Serial 'de.rotex.DAIKINControl' --output-directory $destination --format json |
    Set-Content -LiteralPath (Join-Path $destination 'acquisition.json') -Encoding UTF8
if ($LASTEXITCODE -ne 0) { throw 'Acquisizione REA fallita: consultare il file privato, non pubblicarlo.' }
Write-Output 'APK ed evidenza acquisiti in _private/apk; nessuna installazione o modifica app eseguita.'
