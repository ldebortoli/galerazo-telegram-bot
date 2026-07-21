[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
    throw "No se encontro gcloud. Instala Google Cloud CLI y ejecuta 'gcloud auth login'."
}
foreach ($value in @($ProjectId, $Zone, $Instance)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Parametro GCE invalido: $value"
    }
}

$bootstrap = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\bootstrap.sh")).Path
$verifier = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\verify-host.sh")).Path
$target = "${Instance}:/tmp"

& gcloud compute scp $bootstrap $verifier $target `
    --project $ProjectId --zone $Zone --tunnel-through-iap --quiet
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo copiar el bootstrap a la VM."
}

& gcloud compute ssh $Instance `
    --project $ProjectId --zone $Zone --tunnel-through-iap `
    --command "sudo bash /tmp/galerazo-bootstrap.sh && sudo bash /tmp/verify-host.sh"
if ($LASTEXITCODE -ne 0) {
    throw "El bootstrap de la VM fallo."
}

Write-Host "Host preparado. Ahora completa /etc/galerazo/bot.env dentro de la VM." -ForegroundColor Green
