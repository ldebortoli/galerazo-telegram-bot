[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

foreach ($value in @($ProjectId, $Zone, $Instance)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Parametro GCE invalido: $value"
    }
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

$inspector = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\inspect-secrets.sh")).Path
& $gcloud compute scp $inspector "${Instance}:/tmp/inspect-secrets.sh" `
    --project $ProjectId --zone $Zone --tunnel-through-iap --quiet 1>$null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo copiar el inspector de credenciales."
}

$output = & $gcloud compute ssh $Instance `
    --project $ProjectId --zone $Zone --tunnel-through-iap --quiet `
    --command "sudo bash /tmp/inspect-secrets.sh"
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo consultar el estado de credenciales."
}
$jsonLine = @($output) | Where-Object {
    $trimmed = ([string]$_).Trim()
    $trimmed.StartsWith("{") -and $trimmed.EndsWith("}")
} | Select-Object -Last 1
if (-not $jsonLine) {
    throw "El inspector no devolvio un estado JSON valido."
}
try {
    $parsed = $jsonLine | ConvertFrom-Json
    foreach ($name in @(
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY",
        "TELEGRAM_DEV_USER_IDS",
        "TELEGRAM_LOG_CHAT_ID",
        "TELEGRAM_ANNOUNCEMENTS_CHAT_ID",
        "TELEGRAM_HISOPO_COMMON_FILE_ID",
        "TELEGRAM_HISOPO_SILVER_FILE_ID",
        "TELEGRAM_HISOPO_GOLD_FILE_ID",
        "GOOGLE_SHEETS_SPREADSHEET_ID",
        "GOOGLE_SHEETS_WORKSHEET_NAME",
        "GOOGLE_CLOUD_BILLING_PROJECT_ID",
        "GOOGLE_CLOUD_BILLING_TABLE",
        "GOOGLE_CLOUD_BILLING_REPORT_TIME",
        "GOOGLE_SHEETS_CREDENTIALS_JSON"
    )) {
        $property = $parsed.PSObject.Properties[$name]
        if ($null -eq $property -or $property.Value -isnot [bool]) {
            throw "estado booleano ausente"
        }
    }
}
catch {
    throw "El inspector devolvio una respuesta invalida."
}
Write-Output (($parsed | ConvertTo-Json -Compress -Depth 4))
