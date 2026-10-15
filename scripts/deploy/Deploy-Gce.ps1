[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance,
    [Parameter(Mandatory = $true)][string]$Image
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
    throw "No se encontro gcloud. Instala Google Cloud CLI y autentica tu cuenta."
}
foreach ($value in @($ProjectId, $Zone, $Instance)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Parametro GCE invalido: $value"
    }
}
if ($Image -notmatch '^[A-Za-z0-9][A-Za-z0-9._/:@-]+$') {
    throw "Referencia de imagen invalida: $Image"
}

if ($Image -notmatch '^(?<Location>[a-z][a-z0-9-]*)-docker\.pkg\.dev/(?<Project>[a-z][a-z0-9-]*)/(?<Repository>[a-z][a-z0-9-]*)/galerazobot:[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$' -or $Matches.Project -ne $ProjectId) {
    throw "La retencion requiere una imagen del paquete galerazobot en el proyecto indicado."
}
$registryLocation = $Matches.Location
$registryRepository = $Matches.Repository
$retention = Join-Path $PSScriptRoot "Sync-GceRegistryRetention.ps1"
# Protect the candidate before touching production, even if it was built days ago.
& $retention -ProjectId $ProjectId -Zone $Zone -Instance $Instance `
    -Location $registryLocation -Repository $registryRepository -CandidateImage $Image

$compose = (Resolve-Path (Join-Path $PSScriptRoot "..\..\compose.production.yaml")).Path
$deploy = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\deploy.sh")).Path
$rollback = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\rollback.sh")).Path

foreach ($item in @(
    @($compose, "${Instance}:/tmp/galerazo-compose.yaml"),
    @($deploy, "${Instance}:/tmp/galerazo-deploy.sh"),
    @($rollback, "${Instance}:/tmp/galerazo-rollback.sh")
)) {
    & gcloud compute scp $item[0] $item[1] `
        --project $ProjectId --zone $Zone --tunnel-through-iap --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo copiar $($item[0]) a la VM."
    }
}

$remoteCommand = "sudo bash /tmp/galerazo-deploy.sh '$Image'"
& gcloud compute ssh $Instance `
    --project $ProjectId --zone $Zone --tunnel-through-iap `
    --command $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "El deploy fallo. Revisa la salida anterior: el script remoto restauro la imagen previa cuando existia o detuvo el contenedor fallido."
}

Write-Host "Deploy saludable con $Image; actualizando retencion..." -ForegroundColor Green
& $retention -ProjectId $ProjectId -Zone $Zone -Instance $Instance `
    -Location $registryLocation -Repository $registryRepository
Write-Host "Deploy y retencion completados con $Image" -ForegroundColor Green
