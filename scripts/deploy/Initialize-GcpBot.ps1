[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$Location = "us-central1",
    [string]$Repository = "bots",
    [string]$ServiceAccountId = "galerazo-vm",
    [string]$ServiceAccountDisplayName = "Galerazo production VM",
    [string]$PublisherMember
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-GcloudCommand {
    $command = Get-Command "gcloud" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $fallback = Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }

    throw "No se encontro gcloud. Instala Google Cloud CLI y ejecuta 'gcloud auth login'."
}

function Invoke-Gcloud {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$SuppressOutput
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        if ($SuppressOutput) {
            & $script:GcloudCommand @Arguments 1>$null 2>$null
            $result = $null
        }
        else {
            $result = & $script:GcloudCommand @Arguments 2>$null
        }
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($exitCode -ne 0) {
        throw "Fallo 'gcloud $($Arguments -join ' ')' con codigo $exitCode."
    }
    return $result
}

function Test-Gcloud {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $script:GcloudCommand @Arguments 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Test-PolicyBinding {
    param(
        [Parameter(Mandatory = $true)]$Policy,
        [Parameter(Mandatory = $true)][string]$Role,
        [Parameter(Mandatory = $true)][string]$Member
    )

    foreach ($binding in @($Policy.bindings)) {
        if ($binding.role -eq $Role -and $Member -in @($binding.members)) {
            return $true
        }
    }
    return $false
}

if ($ProjectId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') {
    throw "ProjectId invalido: $ProjectId"
}
if ($Location -notmatch '^[a-z][a-z0-9-]{1,62}$') {
    throw "Location invalida: $Location"
}
if ($Repository -notmatch '^[a-z][a-z0-9._-]{0,62}$') {
    throw "Repository invalido: $Repository"
}
if ($ServiceAccountId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') {
    throw "ServiceAccountId invalido: $ServiceAccountId"
}

$script:GcloudCommand = Resolve-GcloudCommand
$configuredProject = (Invoke-Gcloud -Arguments @("config", "get-value", "project")).Trim()
if ($configuredProject -ne $ProjectId) {
    throw "El proyecto activo es '$configuredProject'. Ejecuta 'gcloud config set project $ProjectId' y reintenta."
}

$activeAccount = (Invoke-Gcloud -Arguments @("config", "get-value", "account")).Trim()
if (-not $activeAccount -or $activeAccount -eq "(unset)" -or $activeAccount -notmatch '@') {
    throw "No hay una cuenta activa en gcloud. Ejecuta 'gcloud auth login'."
}
if (-not $PublisherMember) {
    $memberKind = if ($activeAccount.EndsWith(".gserviceaccount.com")) { "serviceAccount" } else { "user" }
    $PublisherMember = "${memberKind}:$activeAccount"
}
if ($PublisherMember -notmatch '^(user|serviceAccount):[^\s@]+@[^\s@]+$') {
    throw "PublisherMember debe usar el formato user:correo o serviceAccount:correo."
}

$projectState = (Invoke-Gcloud -Arguments @(
    "projects", "describe", $ProjectId,
    "--format=value(lifecycleState)"
)).Trim()
if ($projectState -ne "ACTIVE") {
    throw "El proyecto '$ProjectId' no esta activo."
}

$billingEnabled = (Invoke-Gcloud -Arguments @(
    "billing", "projects", "describe", $ProjectId,
    "--format=value(billingEnabled)"
)).Trim()
if ($billingEnabled -ne "True") {
    throw "El proyecto '$ProjectId' no tiene facturacion habilitada."
}

$requiredApis = @(
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
    "iap.googleapis.com",
    "iamcredentials.googleapis.com"
)
$enabledApis = @(Invoke-Gcloud -Arguments @(
    "services", "list", "--enabled", "--project=$ProjectId",
    "--format=value(config.name)"
))
$missingApis = @($requiredApis | Where-Object { $_ -notin $enabledApis })
if ($missingApis.Count -gt 0) {
    $enableArguments = @("services", "enable") + $missingApis + @("--project=$ProjectId", "--quiet")
    Invoke-Gcloud -Arguments $enableArguments -SuppressOutput
}

$repositoryExists = Test-Gcloud -Arguments @(
    "artifacts", "repositories", "describe", $Repository,
    "--location=$Location", "--project=$ProjectId", "--format=value(format)"
)
if (-not $repositoryExists) {
    Invoke-Gcloud -Arguments @(
        "artifacts", "repositories", "create", $Repository,
        "--repository-format=docker",
        "--location=$Location",
        "--description=Imagenes de bots",
        "--project=$ProjectId",
        "--quiet"
    ) -SuppressOutput
}

$repositoryFormat = (Invoke-Gcloud -Arguments @(
    "artifacts", "repositories", "describe", $Repository,
    "--location=$Location", "--project=$ProjectId",
    "--format=value(format)"
)).Trim()
if ($repositoryFormat -ne "DOCKER") {
    throw "El repositorio '$Repository' existe pero no tiene formato DOCKER."
}

$serviceAccountEmail = "$ServiceAccountId@$ProjectId.iam.gserviceaccount.com"
$serviceAccountExists = Test-Gcloud -Arguments @(
    "iam", "service-accounts", "describe", $serviceAccountEmail,
    "--project=$ProjectId", "--format=value(name)"
)
if (-not $serviceAccountExists) {
    Invoke-Gcloud -Arguments @(
        "iam", "service-accounts", "create", $ServiceAccountId,
        "--display-name=$ServiceAccountDisplayName",
        "--description=Runtime identity for $ServiceAccountId",
        "--project=$ProjectId",
        "--quiet"
    ) -SuppressOutput

    $serviceAccountReady = $false
    for ($attempt = 1; $attempt -le 6; $attempt++) {
        if (Test-Gcloud -Arguments @(
            "iam", "service-accounts", "describe", $serviceAccountEmail,
            "--project=$ProjectId", "--format=value(name)"
        )) {
            $serviceAccountReady = $true
            break
        }
        Start-Sleep -Seconds 5
    }
    if (-not $serviceAccountReady) {
        throw "La service account fue creada pero Google aun no permite leerla. Reintenta en un minuto."
    }
}

$readerMember = "serviceAccount:$serviceAccountEmail"
Invoke-Gcloud -Arguments @(
    "artifacts", "repositories", "add-iam-policy-binding", $Repository,
    "--location=$Location", "--project=$ProjectId",
    "--member=$readerMember",
    "--role=roles/artifactregistry.reader",
    "--quiet"
) -SuppressOutput

Invoke-Gcloud -Arguments @(
    "artifacts", "repositories", "add-iam-policy-binding", $Repository,
    "--location=$Location", "--project=$ProjectId",
    "--member=$PublisherMember",
    "--role=roles/artifactregistry.writer",
    "--quiet"
) -SuppressOutput

$policyJson = Invoke-Gcloud -Arguments @(
    "artifacts", "repositories", "get-iam-policy", $Repository,
    "--location=$Location", "--project=$ProjectId", "--format=json"
)
$policy = ($policyJson -join [Environment]::NewLine) | ConvertFrom-Json
$readerOk = Test-PolicyBinding -Policy $policy -Role "roles/artifactregistry.reader" -Member $readerMember
$writerOk = Test-PolicyBinding -Policy $policy -Role "roles/artifactregistry.writer" -Member $PublisherMember
if (-not $readerOk -or -not $writerOk) {
    throw "No se pudieron verificar los permisos del repositorio."
}

$userManagedKeys = @(Invoke-Gcloud -Arguments @(
    "iam", "service-accounts", "keys", "list",
    "--iam-account=$serviceAccountEmail",
    "--managed-by=user",
    "--project=$ProjectId",
    "--format=value(name)"
) | Where-Object { $_ })
if ($userManagedKeys.Count -gt 0) {
    throw "La service account tiene claves administradas por el usuario. El deploy esperado no usa claves JSON."
}

Write-Host "Fundacion GCP lista." -ForegroundColor Green
Write-Host "Proyecto: $ProjectId" -ForegroundColor DarkGray
Write-Host "Registro: ${Location}-docker.pkg.dev/$ProjectId/$Repository" -ForegroundColor DarkGray
Write-Host "Identidad de runtime: $ServiceAccountId (Reader solo sobre $Repository)" -ForegroundColor DarkGray
Write-Host "Publicador local: Writer solo sobre $Repository" -ForegroundColor DarkGray
Write-Host "Claves administradas por el usuario: 0" -ForegroundColor DarkGray
Write-Host "Este script no crea ninguna VM." -ForegroundColor DarkGray
