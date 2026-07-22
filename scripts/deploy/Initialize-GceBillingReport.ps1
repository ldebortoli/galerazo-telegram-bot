[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$DatasetId = "billing_export",
    [string]$Location = "US",
    [string]$ServiceAccountId = "galerazo-vm",
    [switch]$AcknowledgeBillableResource
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $AcknowledgeBillableResource) {
    throw "BigQuery puede generar costos de almacenamiento y consulta. Reejecuta con -AcknowledgeBillableResource."
}
if ($ProjectId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') {
    throw "ProjectId invalido: $ProjectId"
}
if ($DatasetId -notmatch '^[A-Za-z_][A-Za-z0-9_]{0,1023}$') {
    throw "DatasetId invalido: $DatasetId"
}
if ($Location -notmatch '^[A-Za-z][A-Za-z0-9-]{1,62}$') {
    throw "Location invalida: $Location"
}
if ($ServiceAccountId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') {
    throw "ServiceAccountId invalido: $ServiceAccountId"
}

function Resolve-Tool {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Fallback
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    if (Test-Path -LiteralPath $Fallback) {
        return $Fallback
    }
    throw "No se encontro $Name. Instala Google Cloud CLI."
}

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$SuppressOutput
    )

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        if ($SuppressOutput) {
            & $Command @Arguments 1>$null 2>$null
            $output = $null
        }
        else {
            $output = & $Command @Arguments 2>$null
        }
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0) {
        throw "Fallo una operacion de Google Cloud (codigo $exitCode)."
    }
    return $output
}

function Test-BqDataset {
    param([Parameter(Mandatory = $true)][string]$Identifier)

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $script:Bq show --dataset --format=none $Identifier 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

$gcloudFallback = Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
$bqFallback = Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/bq.cmd"
$script:Gcloud = Resolve-Tool -Name "gcloud" -Fallback $gcloudFallback
$script:Bq = Resolve-Tool -Name "bq" -Fallback $bqFallback

$configuredProject = (Invoke-Native -Command $script:Gcloud -Arguments @(
    "config", "get-value", "project"
)).Trim()
if ($configuredProject -ne $ProjectId) {
    throw "El proyecto activo es '$configuredProject'. Ejecuta 'gcloud config set project $ProjectId'."
}

Invoke-Native -Command $script:Gcloud -Arguments @(
    "services", "enable", "bigquery.googleapis.com",
    "--project=$ProjectId", "--quiet"
) -SuppressOutput

$datasetIdentifier = "${ProjectId}:${DatasetId}"
if (-not (Test-BqDataset -Identifier $datasetIdentifier)) {
    Invoke-Native -Command $script:Bq -Arguments @(
        "mk", "--dataset", "--location=$Location",
        "--description=Cloud Billing standard usage cost export",
        $datasetIdentifier
    ) -SuppressOutput
}

$serviceAccountEmail = "$ServiceAccountId@$ProjectId.iam.gserviceaccount.com"
$member = "serviceAccount:$serviceAccountEmail"
Invoke-Native -Command $script:Gcloud -Arguments @(
    "projects", "add-iam-policy-binding", $ProjectId,
    "--member=$member", "--role=roles/bigquery.jobUser",
    "--condition=None", "--quiet"
) -SuppressOutput
Invoke-Native -Command $script:Bq -Arguments @(
    "add-iam-policy-binding", "--dataset",
    "--member=$member", "--role=roles/bigquery.dataViewer",
    $datasetIdentifier
) -SuppressOutput

Write-Host "Dataset y permisos minimos listos." -ForegroundColor Green
Write-Host "Dataset: $datasetIdentifier" -ForegroundColor DarkGray
Write-Host "Ubicacion: $Location" -ForegroundColor DarkGray
Write-Host "Paso manual: en Facturacion > Exportacion de facturacion, habilita Costo de uso estandar sobre este dataset." -ForegroundColor Yellow
Write-Host "Despues espera la tabla gcp_billing_export_v1_<BILLING_ACCOUNT_ID> y configura GOOGLE_CLOUD_BILLING_TABLE." -ForegroundColor Yellow
