[CmdletBinding()]
param(
    [int]$Tail = 100
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($Tail -lt 1 -or $Tail -gt 10000) {
    throw "Tail debe estar entre 1 y 10000."
}

$gcloudCommand = Get-Command "gcloud" -ErrorAction SilentlyContinue
if ($gcloudCommand) {
    $gcloud = $gcloudCommand.Source
}
else {
    $fallback = Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
    if (-not (Test-Path -LiteralPath $fallback)) {
        throw "No se encontro gcloud. Instala Google Cloud CLI e inicia sesion."
    }
    $gcloud = $fallback
}

Write-Host "Siguiendo logs DEBUG de Galerazo Bot. Se omiten solo getUpdates exitosos. Usa Ctrl+C para detener la lectura." -ForegroundColor Cyan
& $gcloud compute ssh galerazo-prod `
    --project bot-fleet-production `
    --zone us-central1-a `
    --tunnel-through-iap `
    --command "sudo docker compose --env-file /opt/galerazo/image.env -f /opt/galerazo/compose.yaml logs --follow --tail $Tail bot"
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron leer los logs remotos."
}
