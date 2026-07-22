[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance,
    [Parameter(Mandatory = $true)][string]$ServiceAccountName,
    [Parameter(Mandatory = $true)][string]$BotId,
    [string]$Location = "us-central1",
    [string]$BucketName = "",
    [string]$DatabasePath = "/srv/galerazo/data/galerazo.sqlite3",
    [string]$BackupDirectory = "/srv/galerazo/backups/monthly",
    [int]$RuntimeUid = 10001,
    [switch]$AcknowledgePotentialStorageCost
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $AcknowledgePotentialStorageCost) {
    throw "Cloud Storage puede generar cargos si supera el Free Tier. Reejecuta con -AcknowledgePotentialStorageCost."
}
foreach ($value in @($ProjectId, $Zone, $Instance, $ServiceAccountName)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Parametro GCP invalido: $value"
    }
}
if ($Location -notin @("us-west1", "us-central1", "us-east1")) {
    throw "La ubicacion debe ser una region elegible para Cloud Storage Always Free."
}
if ($BotId -notmatch '^[a-z0-9][a-z0-9-]{0,62}$') {
    throw "BotId invalido."
}
foreach ($pathValue in @($DatabasePath, $BackupDirectory)) {
    if ($pathValue -notmatch '^/[A-Za-z0-9._/-]+$' -or $pathValue.Contains("..")) {
        throw "Ruta remota invalida: $pathValue"
    }
}
if ($RuntimeUid -lt 1 -or $RuntimeUid -gt 60000) {
    throw "RuntimeUid invalido."
}

if (-not $BucketName) {
    $BucketName = "$ProjectId-sqlite-backups"
}
if ($BucketName -notmatch '^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$') {
    throw "BucketName invalido."
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$backupRuntime = (Resolve-Path (Join-Path $projectRoot "deploy\gce\sqlite_backup.py")).Path
$remoteInstaller = (Resolve-Path (Join-Path $projectRoot "deploy\gce\install-sqlite-backup.sh")).Path
$lifecycle = (Resolve-Path (Join-Path $projectRoot "deploy\gce\backup-lifecycle.json")).Path

$gcloudCommand = Get-Command "gcloud" -ErrorAction SilentlyContinue
if ($gcloudCommand) {
    $gcloud = $gcloudCommand.Source
}
else {
    $fallback = Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
    if (-not (Test-Path -LiteralPath $fallback)) {
        throw "No se encontro Google Cloud CLI."
    }
    $gcloud = $fallback
}

function Invoke-Gcloud {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$AllowFailure
    )

    & $gcloud @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "Fallo gcloud con codigo $exitCode."
    }
    return $exitCode
}

[void](Invoke-Gcloud -Arguments @("services", "enable", "storage.googleapis.com", "--project=$ProjectId", "--quiet"))

$bucketUri = "gs://$BucketName"
$previousPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = "Continue"
    & $gcloud storage buckets describe $bucketUri --project=$ProjectId --quiet 1>$null 2>$null
    $bucketExists = $LASTEXITCODE -eq 0
}
finally {
    $ErrorActionPreference = $previousPreference
}

if (-not $bucketExists) {
    [void](Invoke-Gcloud -Arguments @(
        "storage", "buckets", "create", $bucketUri,
        "--project=$ProjectId",
        "--location=$Location",
        "--default-storage-class=STANDARD",
        "--uniform-bucket-level-access",
        "--public-access-prevention",
        "--quiet"
    ))
}

[void](Invoke-Gcloud -Arguments @(
    "storage", "buckets", "update", $bucketUri,
    "--project=$ProjectId",
    "--uniform-bucket-level-access",
    "--public-access-prevention",
    "--lifecycle-file=$lifecycle",
    "--quiet"
))

$runtimeIdentity = "serviceAccount:$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"
[void](Invoke-Gcloud -Arguments @(
    "storage", "buckets", "add-iam-policy-binding", $bucketUri,
    "--member=$runtimeIdentity",
    "--role=roles/storage.objectCreator",
    "--quiet"
))

foreach ($item in @(
    @($backupRuntime, "${Instance}:/tmp/bot-fleet-sqlite-backup.py"),
    @($remoteInstaller, "${Instance}:/tmp/install-sqlite-backup.sh")
)) {
    [void](Invoke-Gcloud -Arguments @(
        "compute", "scp", $item[0], $item[1],
        "--project=$ProjectId", "--zone=$Zone", "--tunnel-through-iap", "--quiet"
    ))
}

$remoteCommand = "sudo bash /tmp/install-sqlite-backup.sh '$BotId' '$DatabasePath' '$BackupDirectory' '$BucketName' '400' '$RuntimeUid'"
[void](Invoke-Gcloud -Arguments @(
    "compute", "ssh", $Instance,
    "--project=$ProjectId", "--zone=$Zone", "--tunnel-through-iap", "--quiet",
    "--command=$remoteCommand"
))

[void](Invoke-Gcloud -Arguments @(
    "storage", "ls", "$bucketUri/bots/$BotId/**",
    "--project=$ProjectId"
))

Write-Host "Backups mensuales habilitados para $BotId." -ForegroundColor Green
Write-Host "Destino: $bucketUri/bots/$BotId/"
Write-Host "Retencion: 400 dias; timer persistente mensual con demora aleatoria de hasta 6 horas."
