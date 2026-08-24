[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$requirementsInput = Join-Path $projectRoot "requirements.in"
$requirementsLock = Join-Path $projectRoot "requirements.txt"
$pythonVersionFile = Join-Path $projectRoot ".python-version"
$buildScript = Join-Path $PSScriptRoot "Build-DockerImage.ps1"
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("galerazo-dependency-update-" + [Guid]::NewGuid().ToString("N"))
$updateEnvironment = Join-Path $temporaryRoot "venv"

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

Assert-Command -Name "py"
Assert-Command -Name "git"

$pythonVersion = (Get-Content -LiteralPath $pythonVersionFile -Raw).Trim()
if ($pythonVersion -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
    throw "Version invalida en .python-version: $pythonVersion"
}
$pythonSelector = "-$($Matches[1]).$($Matches[2])"

New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
Push-Location $projectRoot
try {
    $detectedVersion = (& py $pythonSelector -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
    if ($LASTEXITCODE -ne 0 -or $detectedVersion -ne $pythonVersion) {
        throw "Python requerido: $pythonVersion; detectado: $detectedVersion"
    }

    Invoke-Native -Command "py" -Arguments @($pythonSelector, "-m", "venv", $updateEnvironment)
    $environmentPython = Join-Path $updateEnvironment "Scripts\python.exe"
    Invoke-Native -Command $environmentPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Native -Command $environmentPython -Arguments @(
        "-m", "pip", "install", "--upgrade", "--upgrade-strategy", "eager",
        "--requirement", $requirementsInput
    )

    $resolved = @(& $environmentPython -m pip freeze)
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo resolver el lock actualizado de dependencias."
    }
    [System.IO.File]::WriteAllText(
        $requirementsLock,
        (($resolved -join "`n") + "`n"),
        [System.Text.UTF8Encoding]::new($false)
    )

    & git diff --quiet -- requirements.txt
    $dependencyDiff = $LASTEXITCODE
    if ($dependencyDiff -eq 0) {
        Write-Host "Las dependencias estables ya estan actualizadas." -ForegroundColor Green
        return
    }
    if ($dependencyDiff -ne 1) {
        throw "Git no pudo comparar requirements.txt (codigo $dependencyDiff)."
    }

    Write-Host "Se detectaron nuevas versiones estables; validando el lock..." -ForegroundColor Cyan
    Assert-Command -Name "docker"
    Invoke-Native -Command $environmentPython -Arguments @("scripts/runtime_versions.py")
    Invoke-Native -Command $environmentPython -Arguments @("-m", "coverage", "run", "-m", "pytest")
    Invoke-Native -Command $environmentPython -Arguments @("-m", "coverage", "json")
    Invoke-Native -Command $environmentPython -Arguments @("scripts/check_coverage.py")
    Invoke-Native -Command $environmentPython -Arguments @("-m", "compileall", "app.py", "control_panel.py", "galerazo_bot")
    Invoke-Native -Command $environmentPython -Arguments @("-m", "pip", "check")
    Invoke-Native -Command "git" -Arguments @("diff", "--check", "--", "requirements.txt")

    & $buildScript -Tag "dependency-update-validation"
    if ($LASTEXITCODE -ne 0) {
        throw "La validacion Docker de las dependencias fallo."
    }

    Write-Host "Lock de dependencias actualizado y validado." -ForegroundColor Green
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
