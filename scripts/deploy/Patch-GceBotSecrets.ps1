[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance,
    [Parameter(Mandatory = $true)][string]$PatchFile,
    [string]$GoogleSheetsCredentialsFile,
    [switch]$AcknowledgeSecretUpdate
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $AcknowledgeSecretUpdate) {
    throw "La operacion modifica credenciales remotas. Reejecuta con -AcknowledgeSecretUpdate."
}
foreach ($value in @($ProjectId, $Zone, $Instance)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Parametro GCE invalido: $value"
    }
}

$resolvedPatch = (Resolve-Path -LiteralPath $PatchFile).Path
$patchInfo = Get-Item -LiteralPath $resolvedPatch
if ($patchInfo.Length -gt 32768) {
    throw "El parche de credenciales supera 32 KiB."
}
$allowedKeys = @(
    "TELEGRAM_BOT_TOKEN",
    "OPENAI_API_KEY",
    "TELEGRAM_DEV_USER_IDS",
    "TELEGRAM_EXPENSE_USER_IDS",
    "TELEGRAM_OWNER_USER_ID",
    "TELEGRAM_LOG_CHAT_ID",
    "TELEGRAM_ANNOUNCEMENTS_CHAT_ID",
    "TELEGRAM_HISOPO_COMMON_FILE_ID",
    "TELEGRAM_HISOPO_SILVER_FILE_ID",
    "TELEGRAM_HISOPO_GOLD_FILE_ID",
    "TELEGRAM_HISOPO_DIAMOND_FILE_ID",
    "TELEGRAM_HISOPO_FLEETING_FILE_ID",
    "TELEGRAM_HISOPO_MYSTERY_FILE_ID",
    "TELEGRAM_HISOPO_PUTRID_FILE_ID",
    "TELEGRAM_HISOPO_USED_FILE_ID",
    "TELEGRAM_HISOPO_RADIOACTIVE_FILE_ID",
    "TELEGRAM_HISOPO_BOMB_FILE_ID",
    "TELEGRAM_HISOPO_BOMB_DEFUSED_FILE_ID",
    "TELEGRAM_HISOPO_BOMB_EXPLODED_FILE_ID",
    "TELEGRAM_HISOPO_FRENETIC_FILE_ID",
    "TELEGRAM_HISOPO_BLACK_HOLE_FILE_ID",
    "TELEGRAM_HISOPO_EXPIRED_FILE_ID",
    "TELEGRAM_HISOPO_FAKE_FILE_ID",
    "TELEGRAM_HISOPO_TWIN_FILE_ID",
    "TELEGRAM_HISOPO_GIANT_FILE_ID",
    "TELEGRAM_HISOPO_MIRACLE_FILE_ID",
    "TELEGRAM_MINI_APP_URL",
    "TELEGRAM_MINI_APP_SHORT_NAME",
    "MINI_APP_BIND_HOST",
    "MINI_APP_PORT",
    "GOOGLE_SHEETS_SPREADSHEET_ID",
    "GOOGLE_SHEETS_WORKSHEET_NAME",
    "GOOGLE_SHEETS_CASHFLOW_SHEET_PREFIX",
    "GOOGLE_CLOUD_BILLING_PROJECT_ID",
    "GOOGLE_CLOUD_BILLING_TABLE",
    "GOOGLE_CLOUD_BILLING_REPORT_TIME",
    "GOOGLE_SHEETS_CREDENTIALS_JSON"
)
try {
    $patch = [System.IO.File]::ReadAllText($resolvedPatch) | ConvertFrom-Json
}
catch {
    throw "El parche de credenciales no contiene JSON valido."
}
if ($null -eq $patch -or $patch -isnot [PSCustomObject]) {
    throw "El parche de credenciales debe ser un objeto JSON."
}
$updatesProperty = $patch.PSObject.Properties["updates"]
$clearProperty = $patch.PSObject.Properties["clear"]
$updates = if ($null -eq $updatesProperty) { [PSCustomObject]@{} } else { $updatesProperty.Value }
if ($null -eq $updates -or $updates -isnot [PSCustomObject]) {
    throw "updates debe ser un objeto JSON."
}
if ($null -ne $clearProperty -and $clearProperty.Value -isnot [System.Array]) {
    throw "clear debe ser una lista JSON."
}
if ($GoogleSheetsCredentialsFile) {
    $resolvedCredentials = (Resolve-Path -LiteralPath $GoogleSheetsCredentialsFile).Path
    try {
        $credentials = [System.IO.File]::ReadAllText($resolvedCredentials) | ConvertFrom-Json
    }
    catch {
        throw "La credencial de Google Sheets no contiene JSON valido."
    }
    $updates | Add-Member -NotePropertyName "GOOGLE_SHEETS_CREDENTIALS_JSON" `
        -NotePropertyValue $credentials -Force
}
[object[]]$updateKeys = @($updates.PSObject.Properties | ForEach-Object { $_.Name })
[object[]]$clearKeys = if ($null -eq $clearProperty) { @() } else { @($clearProperty.Value) }
$clearKeys = @($clearKeys | Where-Object { $null -ne $_ -and $_ -ne "" })
if ($updateKeys.Count -eq 0 -and $clearKeys.Count -eq 0) {
    throw "El parche no contiene cambios."
}
foreach ($key in @($updateKeys + $clearKeys)) {
    if ($key -notin $allowedKeys) {
        throw "Variable no permitida en el parche: $key"
    }
}
if ($clearKeys -contains "TELEGRAM_BOT_TOKEN") {
    throw "TELEGRAM_BOT_TOKEN no se puede eliminar."
}
foreach ($key in $updateKeys) {
    if ($clearKeys -contains $key) {
        throw "La variable $key no puede reemplazarse y eliminarse a la vez."
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

function Invoke-Gcloud {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & $gcloud @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo una operacion privada de gcloud (codigo $LASTEXITCODE)."
    }
}

$uploadId = [Guid]::NewGuid().ToString("N")
$remoteDirectory = ".galerazo-secret-patch-$uploadId"
$temporaryPatch = $null
if ($GoogleSheetsCredentialsFile) {
    $temporaryPatch = Join-Path ([System.IO.Path]::GetTempPath()) "galerazo-secret-patch-$uploadId.json"
    [System.IO.File]::WriteAllText(
        $temporaryPatch,
        ($patch | ConvertTo-Json -Compress -Depth 20),
        [System.Text.UTF8Encoding]::new($false)
    )
    if ((Get-Item -LiteralPath $temporaryPatch).Length -gt 32768) {
        [System.IO.File]::Delete($temporaryPatch)
        throw "El parche de credenciales supera 32 KiB."
    }
}
$effectivePatch = if ($temporaryPatch) { $temporaryPatch } else { $resolvedPatch }
$installer = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\patch-config.sh")).Path
$verifier = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\verify-host.sh")).Path
$inspector = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\inspect-secrets.sh")).Path
$remoteCreated = $false

try {
    Invoke-Gcloud -Arguments @(
        "compute", "scp", $installer, $verifier, $inspector, "${Instance}:/tmp",
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet"
    )
    Invoke-Gcloud -Arguments @(
        "compute", "ssh", $Instance,
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet",
        "--command", "umask 077 && mkdir '$remoteDirectory' && chmod 0700 '$remoteDirectory'"
    )
    $remoteCreated = $true
    Invoke-Gcloud -Arguments @(
        "compute", "scp", $effectivePatch, "${Instance}:$remoteDirectory/secret-patch.json",
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet"
    )
    $remoteInstall = 'bash /tmp/patch-config.sh "$HOME/' + $remoteDirectory + '"'
    Invoke-Gcloud -Arguments @(
        "compute", "ssh", $Instance,
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet",
        "--command", $remoteInstall
    )
}
finally {
    if ($remoteCreated) {
        $cleanup = "rm -f '$remoteDirectory/secret-patch.json'; rmdir '$remoteDirectory' 2>/dev/null || true"
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
    if ($temporaryPatch -and [System.IO.File]::Exists($temporaryPatch)) {
        [System.IO.File]::Delete($temporaryPatch)
    }
}
