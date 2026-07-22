[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance,
    [string]$EnvFile = ".env",
    [switch]$AcknowledgeSecretUpload
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $AcknowledgeSecretUpload) {
    throw "La carga reemplaza la configuracion secreta remota. Reejecuta con -AcknowledgeSecretUpload."
}
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
        throw "No se encontro gcloud. Instala Google Cloud CLI y ejecuta 'gcloud auth login'."
    }
    $gcloud = $fallback
}

function Invoke-Gcloud {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & $gcloud @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo una operacion segura de gcloud (codigo $LASTEXITCODE)."
    }
}

function ConvertFrom-EnvValue {
    param([AllowEmptyString()][string]$Value)

    $normalized = $Value.Trim()
    if ($normalized.Length -ge 2) {
        $first = $normalized[0]
        $last = $normalized[$normalized.Length - 1]
        if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
            return $normalized.Substring(1, $normalized.Length - 2)
        }
    }
    return $normalized
}

$resolvedEnvFile = (Resolve-Path -LiteralPath $EnvFile).Path
$expectedKeys = @(
    "TELEGRAM_BOT_TOKEN",
    "OPENAI_API_KEY",
    "TELEGRAM_DEV_USER_IDS",
    "TELEGRAM_LOG_CHAT_ID",
    "TELEGRAM_ANNOUNCEMENTS_CHAT_ID",
    "DATABASE_PATH",
    "GOOGLE_SHEETS_CREDENTIALS_JSON_PATH",
    "GOOGLE_SHEETS_SPREADSHEET_ID",
    "GOOGLE_SHEETS_WORKSHEET_NAME",
    "GOOGLE_CLOUD_BILLING_PROJECT_ID",
    "GOOGLE_CLOUD_BILLING_TABLE",
    "GOOGLE_CLOUD_BILLING_REPORT_TIME"
)
$values = @{}
foreach ($line in [System.IO.File]::ReadAllLines($resolvedEnvFile)) {
    if ([string]::IsNullOrWhiteSpace($line) -or $line -match '^\s*#') {
        continue
    }
    $separator = $line.IndexOf('=')
    if ($separator -lt 1) {
        continue
    }
    $key = $line.Substring(0, $separator).Trim()
    if ($key -notin $expectedKeys) {
        continue
    }
    if ($values.ContainsKey($key)) {
        throw "La variable $key aparece mas de una vez en $resolvedEnvFile."
    }
    $value = ConvertFrom-EnvValue -Value $line.Substring($separator + 1)
    if ($value.Contains([char]0) -or $value.Contains("`r") -or $value.Contains("`n")) {
        throw "La variable $key contiene caracteres no admitidos."
    }
    $values[$key] = $value
}
foreach ($key in $expectedKeys) {
    if (-not $values.ContainsKey($key)) {
        $values[$key] = ""
    }
}

$token = $values["TELEGRAM_BOT_TOKEN"]
if ([string]::IsNullOrWhiteSpace($token) -or $token -eq "replace-me") {
    throw "TELEGRAM_BOT_TOKEN falta o conserva el placeholder en $resolvedEnvFile."
}
$values["DATABASE_PATH"] = "/app/data/galerazo.sqlite3"

$credentialsSource = $null
if (-not [string]::IsNullOrWhiteSpace($values["GOOGLE_SHEETS_CREDENTIALS_JSON_PATH"])) {
    $candidate = $values["GOOGLE_SHEETS_CREDENTIALS_JSON_PATH"]
    if (-not [System.IO.Path]::IsPathRooted($candidate)) {
        $candidate = Join-Path (Split-Path -Parent $resolvedEnvFile) $candidate
    }
    $credentialsSource = (Resolve-Path -LiteralPath $candidate).Path
    try {
        [void]([System.IO.File]::ReadAllText($credentialsSource) | ConvertFrom-Json)
    }
    catch {
        throw "El archivo configurado para Google Sheets no contiene JSON valido."
    }
    $values["GOOGLE_SHEETS_CREDENTIALS_JSON_PATH"] = "/app/secrets/google-service-account.json"
}

$uploadId = [Guid]::NewGuid().ToString("N")
$remoteDirectory = ".galerazo-upload-$uploadId"
$temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) "galerazo-secrets-$uploadId"
$temporaryEnv = Join-Path $temporaryDirectory "bot.env"
$installer = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\install-config.sh")).Path
$verifier = (Resolve-Path (Join-Path $PSScriptRoot "..\..\deploy\gce\verify-host.sh")).Path
$remoteCreated = $false

try {
    [void][System.IO.Directory]::CreateDirectory($temporaryDirectory)
    $lines = foreach ($key in $expectedKeys) {
        "$key=$($values[$key])"
    }
    [System.IO.File]::WriteAllText(
        $temporaryEnv,
        (($lines -join "`n") + "`n"),
        [System.Text.UTF8Encoding]::new($false)
    )

    Invoke-Gcloud -Arguments @(
        "compute", "scp", $installer, $verifier, "${Instance}:/tmp",
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet"
    )
    Invoke-Gcloud -Arguments @(
        "compute", "ssh", $Instance,
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet",
        "--command", "umask 077 && mkdir '$remoteDirectory' && chmod 0700 '$remoteDirectory'"
    )
    $remoteCreated = $true
    Invoke-Gcloud -Arguments @(
        "compute", "scp", $temporaryEnv, "${Instance}:$remoteDirectory/bot.env",
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet"
    )
    if ($credentialsSource) {
        Invoke-Gcloud -Arguments @(
            "compute", "scp", $credentialsSource,
            "${Instance}:$remoteDirectory/google-service-account.json",
            "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet"
        )
    }

    $remoteInstall = 'bash /tmp/install-config.sh "$HOME/' + $remoteDirectory + '"'
    Invoke-Gcloud -Arguments @(
        "compute", "ssh", $Instance,
        "--project", $ProjectId, "--zone", $Zone, "--tunnel-through-iap", "--quiet",
        "--command", $remoteInstall
    )
    Write-Host "Secretos configurados en la VM sin mostrar sus valores." -ForegroundColor Green
    Write-Host "OpenAI: $(if ($values['OPENAI_API_KEY']) { 'configurado' } else { 'omitido' })."
    Write-Host "Google Sheets: $(if ($credentialsSource) { 'credencial copiada' } else { 'omitido' })."
}
finally {
    if ($remoteCreated) {
        $cleanup = "rm -f '$remoteDirectory/bot.env' '$remoteDirectory/google-service-account.json'; rmdir '$remoteDirectory' 2>/dev/null || true"
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
    if ([System.IO.File]::Exists($temporaryEnv)) {
        [System.IO.File]::Delete($temporaryEnv)
    }
    if ([System.IO.Directory]::Exists($temporaryDirectory)) {
        [System.IO.Directory]::Delete($temporaryDirectory, $false)
    }
}
