[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance,
    [Parameter(Mandatory = $true)][ValidateSet("status", "triggers", "media", "moderate", "stop", "notify-release")][string]$Action,
    [ValidatePattern('^[A-Za-z0-9_-]{1,2048}$')][string]$TriggerId,
    [ValidateSet("delete-trigger", "block-user", "delete-and-block")][string]$ModerationAction,
    [string]$OutputFile,
    [ValidateSet("started", "succeeded", "failed", "skipped")][string]$ReleaseEvent,
    [ValidateLength(1, 800)][string]$ReleaseDetail,
    [switch]$AcknowledgeModeration,
    [switch]$AcknowledgeStop
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

foreach ($value in @($ProjectId, $Zone, $Instance)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Parametro GCE invalido: $value"
    }
}
if ($Action -in @("media", "moderate") -and -not $TriggerId) {
    throw "TriggerId es obligatorio para $Action."
}
if ($Action -eq "media" -and -not $OutputFile) {
    throw "OutputFile es obligatorio para media."
}
if ($Action -eq "moderate" -and (-not $ModerationAction -or -not $AcknowledgeModeration)) {
    throw "La moderacion requiere accion y confirmacion explicitas."
}
if ($Action -eq "stop" -and -not $AcknowledgeStop) {
    throw "La detencion requiere confirmacion explicita."
}
if ($Action -eq "notify-release" -and -not $ReleaseEvent) {
    throw "ReleaseEvent es obligatorio para notify-release."
}
if ($Action -eq "notify-release" -and $ReleaseEvent -eq "failed" -and -not $ReleaseDetail) {
    throw "ReleaseDetail es obligatorio para informar un release fallido."
}
if ($Action -eq "notify-release" -and $ReleaseEvent -ne "failed" -and $ReleaseDetail) {
    throw "ReleaseDetail solo se admite para un release fallido."
}

$gcloudCommand = Get-Command "gcloud" -ErrorAction SilentlyContinue
if ($gcloudCommand) {
    $gcloud = $gcloudCommand.Source
}
else {
    $fallback = Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
    if (-not (Test-Path -LiteralPath $fallback)) {
        throw "No se encontro gcloud."
    }
    $gcloud = $fallback
}

$vmStatus = (& $gcloud compute instances describe $Instance --project $ProjectId --zone $Zone --format "value(status)" --quiet).Trim().ToLowerInvariant()
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo consultar la VM."
}
if ($vmStatus -ne "running") {
    if ($Action -ne "status") {
        throw "La VM esta $vmStatus; no se puede ejecutar $Action."
    }
    $offline = @{
        observedAt = [DateTime]::UtcNow.ToString("o")
        vm = @{ status = $vmStatus }
        container = @{ exists = $false; status = "unreachable"; running = $false; health = "unavailable"; restartCount = 0; recentRestarts = 0; restartLoop = $false; image = $null; startedAt = $null }
        telegram = @{ connected = $false; username = $null; error = "La VM no esta en ejecucion." }
        resources = @{ cpuPercent = $null; memoryUsage = $null; memoryPercent = $null; diskUsedBytes = $null; diskTotalBytes = $null; diskPercent = $null }
        database = @{ available = $false; bytes = $null }
        logs = @()
        errors = @()
        alerts = @("La VM esta $vmStatus.")
    }
    Write-Output (($offline | ConvertTo-Json -Compress -Depth 6))
    exit 0
}

$botctl = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\botctl.py")).Path
$suffix = [Guid]::NewGuid().ToString("N")
$remoteScript = "/tmp/galerazo-botctl-$suffix.py"
$remoteMedia = if ($Action -eq "media") { "/tmp/galerazo-media-$suffix.bin" } else { $null }
$resolvedOutput = if ($OutputFile) { [IO.Path]::GetFullPath($OutputFile) } else { $null }

try {
    & $gcloud compute scp $botctl "${Instance}:$remoteScript" `
        --project $ProjectId --zone $Zone --tunnel-through-iap --quiet 1>$null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo copiar botctl a la VM."
    }

    $remoteArguments = @("sudo", "python3", $remoteScript, $Action)
    if ($Action -eq "media") {
        $remoteArguments += @($TriggerId, $remoteMedia)
    }
    elseif ($Action -eq "moderate") {
        $remoteArguments += @($TriggerId, $ModerationAction)
    }
    elseif ($Action -eq "notify-release") {
        $remoteArguments += @($ReleaseEvent)
        if ($ReleaseDetail) {
            $detailBytes = [Text.Encoding]::UTF8.GetBytes($ReleaseDetail)
            $remoteArguments += [Convert]::ToBase64String($detailBytes)
        }
    }
    $remoteCommand = $remoteArguments -join " "
    $output = & $gcloud compute ssh $Instance `
        --project $ProjectId --zone $Zone --tunnel-through-iap --quiet `
        --command $remoteCommand
    if ($LASTEXITCODE -ne 0) {
        throw "La accion botctl $Action fallo en la VM."
    }

    $jsonLine = @($output) | Where-Object {
        $trimmed = ([string]$_).Trim()
        $trimmed.StartsWith("{") -and $trimmed.EndsWith("}")
    } | Select-Object -Last 1
    if (-not $jsonLine) {
        throw "botctl no devolvio JSON valido."
    }
    try {
        $parsed = $jsonLine | ConvertFrom-Json
    }
    catch {
        throw "botctl devolvio una respuesta invalida."
    }

    if ($Action -eq "media") {
        $parent = Split-Path -Parent $resolvedOutput
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        & $gcloud compute scp "${Instance}:$remoteMedia" $resolvedOutput `
            --project $ProjectId --zone $Zone --tunnel-through-iap --quiet 1>$null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $resolvedOutput)) {
            throw "No se pudo descargar la multimedia del trigger."
        }
    }
    Write-Output (($parsed | ConvertTo-Json -Compress -Depth 8))
}
finally {
    $cleanupTargets = @($remoteScript)
    if ($remoteMedia) { $cleanupTargets += $remoteMedia }
    $cleanupCommand = "sudo rm -f -- " + ($cleanupTargets -join " ")
    & $gcloud compute ssh $Instance `
        --project $ProjectId --zone $Zone --tunnel-through-iap --quiet `
        --command $cleanupCommand 1>$null 2>$null
}
