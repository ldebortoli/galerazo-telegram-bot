[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
    throw "No se encontro gcloud."
}
foreach ($value in @($ProjectId, $Zone, $Instance)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Parametro GCE invalido: $value"
    }
}

& gcloud compute ssh $Instance `
    --project $ProjectId --zone $Zone --tunnel-through-iap `
    --command "sudo bash /opt/galerazo/rollback.sh"
if ($LASTEXITCODE -ne 0) {
    throw "El rollback fallo. Revisa los logs remotos antes de otro intento."
}

Write-Host "Rollback completado." -ForegroundColor Green
