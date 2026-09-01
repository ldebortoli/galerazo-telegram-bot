[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$Location = "us-central1",
    [string]$Repository = "bots",
    [string]$Tag,
    [switch]$SkipBuild,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$buildScript = Join-Path $PSScriptRoot "Build-DockerImage.ps1"
$broadcastValidator = Join-Path $projectRoot "scripts\check_release_broadcast.py"
$runtimeValidator = Join-Path $projectRoot "scripts\runtime_versions.py"

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encontro '$Name' en PATH."
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
Assert-Command -Name "gcloud"
Assert-Command -Name "git"

$projectPython = $null
$pythonPrefixArguments = @()
foreach ($candidate in @(
    (Join-Path $projectRoot ".venv\Scripts\python.exe"),
    (Join-Path $projectRoot ".venv/bin/python")
)) {
    if (Test-Path -LiteralPath $candidate) {
        $projectPython = $candidate
        break
    }
}
if (-not $projectPython) {
    $pythonLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pythonLauncher) {
        $projectPython = $pythonLauncher.Source
        $pythonPrefixArguments = @("-3.14")
    }
    else {
        $pythonCommand = Get-Command "python" -ErrorAction SilentlyContinue
        if (-not $pythonCommand) {
            throw "No se encontro Python para validar el runtime y el broadcast de novedades."
        }
        $projectPython = $pythonCommand.Source
    }
}
Invoke-Native -Command $projectPython -Arguments @($pythonPrefixArguments + $runtimeValidator)
Invoke-Native -Command $projectPython -Arguments @($pythonPrefixArguments + $broadcastValidator)

foreach ($value in @($ProjectId, $Location, $Repository)) {
    if ($value -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]*$') {
        throw "Valor no valido para publicar una imagen: $value"
    }
}

if (-not $Tag) {
    $Tag = (& git -C $projectRoot rev-parse --short=12 HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $Tag) {
        throw "No se pudo obtener el commit actual."
    }
}
if ($Tag -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$') {
    throw "Tag Docker invalido: $Tag"
}

$localImage = "galerazo-bot:$Tag"
$registryHost = "${Location}-docker.pkg.dev"
$remoteImage = "$registryHost/$ProjectId/$Repository/galerazobot:$Tag"

if (-not $SkipBuild) {
    & $buildScript -Tag $Tag -SkipTests:$SkipTests
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo la construccion local de la imagen."
    }
}

Invoke-Native -Command "gcloud" -Arguments @("auth", "configure-docker", $registryHost, "--quiet")
Invoke-Native -Command "docker" -Arguments @("tag", $localImage, $remoteImage)
Invoke-Native -Command "docker" -Arguments @("push", $remoteImage)

$outputDirectory = Join-Path $projectRoot "deploy\out"
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
Set-Content -LiteralPath (Join-Path $outputDirectory "last-image.txt") -Value $remoteImage -Encoding ascii

Write-Host "Imagen publicada: $remoteImage" -ForegroundColor Green
Write-Host "Referencia guardada en deploy\out\last-image.txt" -ForegroundColor DarkGray
