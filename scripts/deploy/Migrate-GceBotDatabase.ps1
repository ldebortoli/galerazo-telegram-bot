[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance,
    [string]$DatabaseFile = "data\galerazo.sqlite3",
    [string]$BackupsDirectory = "backups",
    [switch]$AcknowledgeDataMigration
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $AcknowledgeDataMigration) {
    throw "La migracion reemplaza la base remota. Reejecuta con -AcknowledgeDataMigration."
}
foreach ($value in @($ProjectId, $Zone, $Instance)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Parametro GCE invalido: $value"
    }
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Falta .venv. Ejecuta scripts/setup.ps1 antes de migrar la base."
}

$pidFile = Join-Path $projectRoot "data\bot.pid"
if (Test-Path -LiteralPath $pidFile) {
    $pidText = [System.IO.File]::ReadAllText($pidFile).Trim()
    $processId = 0
    if ([int]::TryParse($pidText, [ref]$processId)) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            throw "El bot local sigue activo (PID $processId). Apagalo antes de migrar SQLite."
        }
    }
}

$databaseCandidate = if ([System.IO.Path]::IsPathRooted($DatabaseFile)) {
    $DatabaseFile
}
else {
    Join-Path $projectRoot $DatabaseFile
}
$backupsCandidate = if ([System.IO.Path]::IsPathRooted($BackupsDirectory)) {
    $BackupsDirectory
}
else {
    Join-Path $projectRoot $BackupsDirectory
}
$resolvedDatabase = (Resolve-Path -LiteralPath $databaseCandidate).Path
if (-not [System.IO.File]::Exists($resolvedDatabase)) {
    throw "No existe la base local: $resolvedDatabase"
}
if (-not [System.IO.Directory]::Exists($backupsCandidate)) {
    [void][System.IO.Directory]::CreateDirectory($backupsCandidate)
}
$resolvedBackups = (Resolve-Path -LiteralPath $backupsCandidate).Path

$gcloudCommand = Get-Command "gcloud" -ErrorAction SilentlyContinue
if ($gcloudCommand) {
    $gcloud = $gcloudCommand.Source
}
else {
    $fallback = Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
    if (-not (Test-Path -LiteralPath $fallback)) {
        throw "No se encontro gcloud. Instala Google Cloud CLI y ejecuta 'gcloud auth login'."
    }
    $gcloud = $fallback
}

function Invoke-Gcloud {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & $gcloud @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo una operacion de migracion por gcloud (codigo $LASTEXITCODE)."
    }
}

$backupCommand = @'
import sys
from pathlib import Path
from galerazo_bot.database import Database

backup = Database(Path(sys.argv[1])).create_backup(Path(sys.argv[2]))
print(backup.resolve())
'@
$backupOutput = & $python -c $backupCommand $resolvedDatabase $resolvedBackups
if ($LASTEXITCODE -ne 0 -or -not $backupOutput) {
    throw "No se pudo crear el backup SQLite consistente."
}
$backupPath = (Resolve-Path -LiteralPath ([string](@($backupOutput)[-1])).Trim()).Path

$integrityCommand = @'
import sqlite3
import sys

connection = sqlite3.connect(f'file:{sys.argv[1]}?mode=ro', uri=True)
try:
    result = connection.execute('PRAGMA integrity_check').fetchone()[0]
finally:
    connection.close()
if result != 'ok':
    raise SystemExit('SQLite integrity_check failed')
print('LOCAL_BACKUP_INTEGRITY=ok')
'@
& $python -c $integrityCommand $backupPath
if ($LASTEXITCODE -ne 0) {
    throw "El backup local no paso integrity_check."
}

$uploadId = [Guid]::NewGuid().ToString("N")
$remoteDirectory = ".galerazo-db-upload-$uploadId"
$installer = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\install-database.sh")).Path
$remoteCreated = $false

try {
    Invoke-Gcloud -Arguments @(
        "compute", "scp", $installer, "${Instance}:/tmp/install-database.sh",
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet"
    )
    Invoke-Gcloud -Arguments @(
        "compute", "ssh", $Instance,
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet",
        "--command", "umask 077 && mkdir '$remoteDirectory' && chmod 0700 '$remoteDirectory'"
    )
    $remoteCreated = $true
    Invoke-Gcloud -Arguments @(
        "compute", "scp", $backupPath, "${Instance}:$remoteDirectory/galerazo.sqlite3",
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet"
    )

    $remoteInstall = 'bash /tmp/install-database.sh "$HOME/' + $remoteDirectory + '"'
    Invoke-Gcloud -Arguments @(
        "compute", "ssh", $Instance,
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet",
        "--command", $remoteInstall
    )
    Write-Host "SQLite migrado y validado sin iniciar el bot." -ForegroundColor Green
    Write-Host "Backup local conservado en: $backupPath"
}
finally {
    if ($remoteCreated) {
        $cleanup = "rm -f '$remoteDirectory/galerazo.sqlite3'; rmdir '$remoteDirectory' 2>/dev/null || true"
        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & $gcloud compute ssh $Instance `
                --project $ProjectId --zone $Zone --tunnel-through-iap --quiet `
                --command $cleanup 1>$null 2>$null
        }
        finally {
            $ErrorActionPreference = $previousPreference
        }
    }
}
