[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Foundation", "Infrastructure", "Prepare", "Configure", "MigrateData", "Publish", "Deploy", "Release", "Rollback")]
    [string]$Action,
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$Location = "us-central1",
    [string]$Repository = "bots",
    [string]$Region = "us-central1",
    [string]$Zone = "us-central1-a",
    [string]$Network = "bot-fleet",
    [string]$Subnet = "bots-us-central1",
    [string]$Instance = "galerazo-prod",
    [string]$ServiceAccountId = "galerazo-vm",
    [string]$ServiceAccountDisplayName = "Galerazo production VM",
    [string]$EnvFile = ".env",
    [string]$DatabaseFile = "data\galerazo.sqlite3",
    [string]$BackupsDirectory = "backups",
    [string]$Image,
    [switch]$SkipTests,
    [switch]$AcknowledgeBillableResource,
    [switch]$AcknowledgeSecretUpload,
    [switch]$AcknowledgeDataMigration,
    [switch]$AcknowledgeProductionDeploy
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$foundationScript = Join-Path $PSScriptRoot "Initialize-GcpBot.ps1"
$infrastructureScript = Join-Path $PSScriptRoot "New-GceBotInstance.ps1"
$hostScript = Join-Path $PSScriptRoot "Initialize-GceHost.ps1"
$secretsScript = Join-Path $PSScriptRoot "Set-GceBotSecrets.ps1"
$databaseMigrationScript = Join-Path $PSScriptRoot "Migrate-GceBotDatabase.ps1"
$publishScript = Join-Path $PSScriptRoot "Publish-DockerImage.ps1"
$deployScript = Join-Path $PSScriptRoot "Deploy-Gce.ps1"
$rollbackScript = Join-Path $PSScriptRoot "Rollback-Gce.ps1"
$lastImageFile = Join-Path $projectRoot "deploy\out\last-image.txt"

function Add-InstalledCommandToPath {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Fallbacks
    )

    if (Get-Command $Name -ErrorAction SilentlyContinue) {
        return
    }
    foreach ($fallback in $Fallbacks) {
        if (Test-Path -LiteralPath $fallback) {
            $directory = Split-Path -Parent $fallback
            $env:Path = "$directory;$env:Path"
            return
        }
    }
    throw "No se encontro '$Name'. Revisa los requisitos de docs/DEPLOY_GCE.md."
}

function Invoke-Foundation {
    & $foundationScript `
        -ProjectId $ProjectId `
        -Location $Location `
        -Repository $Repository `
        -ServiceAccountId $ServiceAccountId `
        -ServiceAccountDisplayName $ServiceAccountDisplayName
}

function Invoke-Infrastructure {
    Invoke-Foundation
    & $infrastructureScript `
        -ProjectId $ProjectId `
        -Region $Region `
        -Zone $Zone `
        -Network $Network `
        -Subnet $Subnet `
        -Instance $Instance `
        -ServiceAccountId $ServiceAccountId `
        -AcknowledgeBillableResource:$AcknowledgeBillableResource
}

function Invoke-Prepare {
    Invoke-Infrastructure
    & $hostScript -ProjectId $ProjectId -Zone $Zone -Instance $Instance
    Write-Host "Pausa manual obligatoria antes del primer deploy:" -ForegroundColor Yellow
    Write-Host "1. Ejecuta -Action Configure -AcknowledgeSecretUpload para transferir .env por IAP." -ForegroundColor Yellow
    Write-Host "2. Apaga el bot local y ejecuta -Action MigrateData -AcknowledgeDataMigration." -ForegroundColor Yellow
    Write-Host "3. Ejecuta este orquestador con -Action Release y -AcknowledgeProductionDeploy." -ForegroundColor Yellow
}

function Invoke-Configure {
    & $secretsScript `
        -ProjectId $ProjectId `
        -Zone $Zone `
        -Instance $Instance `
        -EnvFile $EnvFile `
        -AcknowledgeSecretUpload:$AcknowledgeSecretUpload
}

function Invoke-MigrateData {
    & $databaseMigrationScript `
        -ProjectId $ProjectId `
        -Zone $Zone `
        -Instance $Instance `
        -DatabaseFile $DatabaseFile `
        -BackupsDirectory $BackupsDirectory `
        -AcknowledgeDataMigration:$AcknowledgeDataMigration
}

function Invoke-Publish {
    & $publishScript `
        -ProjectId $ProjectId `
        -Location $Location `
        -Repository $Repository `
        -SkipTests:$SkipTests
}

function Resolve-ReleaseImage {
    if ($Image) {
        $resolvedImage = $Image.Trim()
    }
    elseif (Test-Path -LiteralPath $lastImageFile) {
        $resolvedImage = (Get-Content -LiteralPath $lastImageFile -Raw).Trim()
    }
    else {
        throw "No se encontro una imagen publicada. Ejecuta -Action Publish o indica -Image."
    }

    $expectedPrefix = "$Location-docker.pkg.dev/$ProjectId/$Repository/galerazobot:"
    if (-not $resolvedImage.StartsWith($expectedPrefix)) {
        throw "La imagen no pertenece al registro esperado: $expectedPrefix"
    }
    $tag = $resolvedImage.Substring($expectedPrefix.Length)
    if ($tag -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$' -or $tag -eq "latest") {
        throw "La imagen debe usar un tag inmutable valido y distinto de latest."
    }
    return $resolvedImage
}

function Assert-LocalBotStopped {
    $pidFile = Join-Path $projectRoot "data\bot.pid"
    if (-not (Test-Path -LiteralPath $pidFile)) {
        return
    }
    $pidText = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    $processId = 0
    if ([int]::TryParse($pidText, [ref]$processId)) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            throw "El bot local sigue activo (PID $processId). Apagalo antes del deploy remoto."
        }
    }
}

function Assert-RemoteManualGate {
    $remoteCheck = "sudo test -s /etc/galerazo/bot.env && sudo test -s /srv/galerazo/data/galerazo.sqlite3"
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & gcloud compute ssh $Instance `
            --project $ProjectId --zone $Zone --tunnel-through-iap --quiet `
            --command $remoteCheck 1>$null 2>$null
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($exitCode -ne 0) {
        throw "Faltan el archivo secreto remoto o la base migrada. Completa la pausa manual de la guia."
    }
}

function Invoke-Deploy {
    if (-not $AcknowledgeProductionDeploy) {
        throw "El deploy modifica produccion. Reejecuta con -AcknowledgeProductionDeploy."
    }
    Assert-LocalBotStopped
    Assert-RemoteManualGate
    $releaseImage = Resolve-ReleaseImage
    & $deployScript `
        -ProjectId $ProjectId `
        -Zone $Zone `
        -Instance $Instance `
        -Image $releaseImage
}

function Invoke-Release {
    if (-not $AcknowledgeProductionDeploy) {
        throw "El release publica y despliega produccion. Reejecuta con -AcknowledgeProductionDeploy."
    }
    Assert-LocalBotStopped
    Assert-RemoteManualGate
    Invoke-Publish
    Invoke-Deploy
}

function Invoke-Rollback {
    if (-not $AcknowledgeProductionDeploy) {
        throw "El rollback modifica produccion. Reejecuta con -AcknowledgeProductionDeploy."
    }
    & $rollbackScript -ProjectId $ProjectId -Zone $Zone -Instance $Instance
}

$localAppDataGcloud = Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
$dockerProgramFiles = Join-Path $env:ProgramFiles "Docker/Docker/resources/bin/docker.exe"
Add-InstalledCommandToPath -Name "gcloud" -Fallbacks @($localAppDataGcloud)

if ($Action -in @("Publish", "Release")) {
    Add-InstalledCommandToPath -Name "docker" -Fallbacks @($dockerProgramFiles)
}

switch ($Action) {
    "Foundation" { Invoke-Foundation }
    "Infrastructure" { Invoke-Infrastructure }
    "Prepare" { Invoke-Prepare }
    "Configure" { Invoke-Configure }
    "MigrateData" { Invoke-MigrateData }
    "Publish" { Invoke-Publish }
    "Deploy" { Invoke-Deploy }
    "Release" { Invoke-Release }
    "Rollback" { Invoke-Rollback }
}
