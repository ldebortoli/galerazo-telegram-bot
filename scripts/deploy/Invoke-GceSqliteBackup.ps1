[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet("Run", "Status")][string]$Action,
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance,
    [Parameter(Mandatory = $true)][string]$BotId
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

foreach ($value in @($ProjectId, $Zone, $Instance)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Parametro GCE invalido: $value"
    }
}
if ($BotId -notmatch '^[a-z0-9][a-z0-9-]{0,62}$') {
    throw "BotId invalido."
}

$gcloudCommand = Get-Command "gcloud" -ErrorAction SilentlyContinue
$gcloud = if ($gcloudCommand) {
    $gcloudCommand.Source
}
else {
    Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
}
if (-not (Test-Path -LiteralPath $gcloud) -and -not $gcloudCommand) {
    throw "No se encontro Google Cloud CLI."
}

$unit = "bot-fleet-sqlite-backup-$BotId"
$runPrefix = if ($Action -eq "Run") { "sudo systemctl start '$unit.service' && " } else { "" }
$remoteCommand = $runPrefix + "sudo systemctl is-enabled '$unit.timer' && sudo systemctl is-active '$unit.timer' && sudo systemctl show '$unit.timer' --property=NextElapseUSecRealtime --value && sudo systemctl show '$unit.service' --property=Result --value && sudo journalctl -u '$unit.service' --no-pager -n 4"

& $gcloud compute ssh $Instance `
    --project=$ProjectId --zone=$Zone --tunnel-through-iap --quiet `
    --command=$remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo ejecutar la accion de backup $Action."
}
