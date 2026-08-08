[CmdletBinding()]
param(
    [string]$Tag,
    [string]$ImageName = "galerazo-bot",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encontro '$Name'. Instala Docker Desktop y confirma que usa contenedores Linux."
    }
}

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo '$Command $($Arguments -join ' ')' con codigo $LASTEXITCODE."
    }
}

Assert-Command -Name "docker"

if (-not $Tag) {
    Assert-Command -Name "git"
    $Tag = (& git -C $projectRoot rev-parse --short=12 HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $Tag) {
        throw "No se pudo obtener el commit actual para etiquetar la imagen."
    }
}

if ($Tag -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$') {
    throw "Tag Docker invalido: $Tag"
}
if ($ImageName -notmatch '^[A-Za-z0-9][A-Za-z0-9._/-]*$') {
    throw "Nombre de imagen Docker invalido: $ImageName"
}

$runtimeImage = "${ImageName}:$Tag"
$testImage = "${ImageName}:test-$Tag"

Push-Location $projectRoot
try {
    if (-not $SkipTests) {
        Write-Host "Construyendo target de pruebas $testImage..." -ForegroundColor Cyan
        Invoke-Native -Command "docker" -Arguments @(
            "build", "--platform", "linux/amd64", "--target", "test",
            "--tag", $testImage, "."
        )
        Invoke-Native -Command "docker" -Arguments @(
            "run", "--rm", $testImage,
            "python", "-m", "pytest"
        )
        Invoke-Native -Command "docker" -Arguments @(
            "run", "--rm", $testImage, "python", "scripts/runtime_versions.py"
        )
    }

    Write-Host "Construyendo imagen de produccion $runtimeImage..." -ForegroundColor Cyan
    Invoke-Native -Command "docker" -Arguments @(
        "build", "--platform", "linux/amd64", "--target", "runtime",
        "--tag", $runtimeImage, "."
    )
    Invoke-Native -Command "docker" -Arguments @(
        "run", "--rm", $runtimeImage,
        "python", "-c",
        "from galerazo_bot.runtime import ensure_python_version; ensure_python_version(); print('Runtime image version check OK')"
    )
}
finally {
    Pop-Location
}

Write-Host "Imagen local lista: $runtimeImage" -ForegroundColor Green
