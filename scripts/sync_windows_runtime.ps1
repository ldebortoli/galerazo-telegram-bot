[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$ForceRecreate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$version = (Get-Content -LiteralPath (Join-Path $projectRoot ".python-version") -Raw).Trim()
if ($version -notmatch "^(\d+)\.(\d+)\.(\d+)$") {
    throw "Version invalida en .python-version: $version"
}
$series = "$($Matches[1]).$($Matches[2])"

function Get-PythonLauncher {
    $command = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $localLauncher = Join-Path $env:LocalAppData "Programs\Python\Launcher\py.exe"
    if (Test-Path -LiteralPath $localLauncher) {
        return $localLauncher
    }
    return $null
}

function Test-ExpectedPython {
    param([string]$Launcher)

    if (-not $Launcher) {
        return $false
    }
    $detected = & $Launcher "-$series" --version 2>&1
    return $LASTEXITCODE -eq 0 -and $detected -eq "Python $version"
}

$pythonLauncher = Get-PythonLauncher
if (-not (Test-ExpectedPython -Launcher $pythonLauncher)) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "No se encontro winget. Instalalo desde App Installer para poder instalar Python $version."
    }

    $packageId = "Python.Python.$series"
    & $winget.Source list --id $packageId --exact --accept-source-agreements | Out-Null
    if ($LASTEXITCODE -eq 0) {
        & $winget.Source upgrade --id $packageId --exact --silent `
            --accept-package-agreements --accept-source-agreements --disable-interactivity
    } else {
        & $winget.Source install --id $packageId --exact --silent `
            --accept-package-agreements --accept-source-agreements --disable-interactivity
    }
    if ($LASTEXITCODE -ne 0) {
        throw "winget no pudo instalar Python $version desde el paquete $packageId."
    }
    $pythonLauncher = Get-PythonLauncher
}

if (-not (Test-ExpectedPython -Launcher $pythonLauncher)) {
    throw "No se pudo activar Python $version mediante py.exe."
}

$venvPath = [IO.Path]::GetFullPath((Join-Path $projectRoot ".venv"))
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$recreateVenv = $ForceRecreate -or -not (Test-Path -LiteralPath $venvPython)
if (-not $recreateVenv) {
    $venvVersion = & $venvPython --version 2>&1
    $recreateVenv = $LASTEXITCODE -ne 0 -or $venvVersion -ne "Python $version"
}

if ($recreateVenv -and (Test-Path -LiteralPath $venvPath)) {
    $expectedRoot = [IO.Path]::GetFullPath($projectRoot).TrimEnd('\') + '\'
    if (-not $venvPath.StartsWith($expectedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "La ruta de .venv queda fuera del proyecto: $venvPath"
    }
    $venvItem = Get-Item -LiteralPath $venvPath -Force
    if ($venvItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Por seguridad no se elimina una .venv que sea un enlace o junction."
    }
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

if ($recreateVenv) {
    Write-Host "Creando .venv con Python $version..."
    & $pythonLauncher "-$series" -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear .venv con Python $version."
    }
} else {
    Write-Host ".venv ya usa Python $version; se conserva."
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo actualizar pip."
}
& $venvPython -m pip install --requirement (Join-Path $projectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo instalar requirements.txt."
}
& $venvPython (Join-Path $projectRoot "scripts\runtime_versions.py")
if ($LASTEXITCODE -ne 0) {
    throw "Windows, Docker y .python-version no estan alineados."
}
& $venvPython -m compileall -q `
    (Join-Path $projectRoot "app.py") `
    (Join-Path $projectRoot "control_panel.py") `
    (Join-Path $projectRoot "galerazo_bot") `
    (Join-Path $projectRoot "scripts")
if ($LASTEXITCODE -ne 0) {
    throw "La compilacion de los modulos Python fallo."
}
if (-not $SkipTests) {
    & $venvPython -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "La suite fallo con el runtime sincronizado."
    }
}
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "pip check encontro dependencias incompatibles."
}

Write-Host "Runtime de Windows listo con Python $version."
