$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$version = (Get-Content -LiteralPath (Join-Path $projectRoot ".python-version") -Raw).Trim()
if ($version -notmatch "^(\d+)\.(\d+)\.(\d+)$") {
    throw "Version invalida en .python-version: $version"
}
$series = "$($Matches[1]).$($Matches[2])"

$installedVersion = & py "-$series" --version 2>&1
if ($LASTEXITCODE -ne 0 -or $installedVersion -ne "Python $version") {
    $packageId = "Python.Python.$series"
    winget list --id $packageId --exact --accept-source-agreements | Out-Null
    if ($LASTEXITCODE -eq 0) {
        winget upgrade --id $packageId --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    } else {
        winget install --id $packageId --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    }
    if ($LASTEXITCODE -ne 0) {
        throw "winget no pudo instalar Python $version desde el paquete $packageId."
    }
}

$verifiedVersion = & py "-$series" --version 2>&1
if ($LASTEXITCODE -ne 0 -or $verifiedVersion -ne "Python $version") {
    throw "No se pudo activar Python $version. Version detectada: $verifiedVersion"
}

$venvPath = Join-Path $projectRoot ".venv"
if (Test-Path -LiteralPath $venvPath) {
    $resolvedVenv = (Resolve-Path -LiteralPath $venvPath).Path
    if ($resolvedVenv -ne $venvPath) {
        throw "Ruta .venv inesperada: $resolvedVenv"
    }
    Remove-Item -LiteralPath $resolvedVenv -Recurse -Force
}

& py "-$series" -m venv $venvPath
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear .venv con Python $version." }
$python = Join-Path $venvPath "Scripts\python.exe"
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "No se pudo actualizar pip." }
& $python -m pip install --requirement (Join-Path $projectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar requirements.txt." }
& $python (Join-Path $projectRoot "scripts\runtime_versions.py")
if ($LASTEXITCODE -ne 0) { throw "Windows, Docker y .python-version no estan alineados." }
& $python -m unittest discover -s (Join-Path $projectRoot "tests") -v
if ($LASTEXITCODE -ne 0) { throw "La suite fallo con el runtime sincronizado." }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw "pip check encontro dependencias incompatibles." }

Write-Output "Windows runtime synchronized on Python $version."
