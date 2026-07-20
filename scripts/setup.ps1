[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$NoLaunch,
    [switch]$ForceRecreate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSEdition -eq "Core" -and -not $IsWindows) {
    throw "Este setup prepara la ejecucion local y el panel nativo de Windows."
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeScript = Join-Path $PSScriptRoot "sync_windows_runtime.ps1"
$buildScript = Join-Path $projectRoot "build_control_panel.ps1"
$envExamplePath = Join-Path $projectRoot ".env.example"
$envPath = Join-Path $projectRoot ".env"
$launcherPath = Join-Path $projectRoot "bin\GalerazoBotControl.exe"

foreach ($requiredPath in @(
    $runtimeScript,
    $buildScript,
    $envExamplePath,
    (Join-Path $projectRoot "requirements.txt"),
    (Join-Path $projectRoot ".python-version")
)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Falta un archivo requerido para preparar Galerazo Bot: $requiredPath"
    }
}

Write-Host "Preparando el runtime y las dependencias de Galerazo Bot..."
$runtimeArguments = @{}
if ($SkipTests) {
    $runtimeArguments["SkipTests"] = $true
}
if ($ForceRecreate) {
    $runtimeArguments["ForceRecreate"] = $true
}
& $runtimeScript @runtimeArguments

if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $envExamplePath -Destination $envPath
    Write-Host "Se creo .env desde .env.example. Completa los secretos desde el panel."
} else {
    Write-Host "Se conserva el archivo .env existente."
}

foreach ($directory in @("data", "data\backups", "backups", "debug")) {
    New-Item -ItemType Directory -Force `
        -Path (Join-Path $projectRoot $directory) | Out-Null
}

Write-Host "Compilando el lanzador y creando accesos directos..."
& $buildScript
if (-not (Test-Path -LiteralPath $launcherPath)) {
    throw "La instalacion termino sin generar $launcherPath."
}

Write-Host ""
Write-Host "Instalacion y validacion terminadas."
Write-Host "La configuracion local se administra desde Galerazo Bot - Control."
if (-not $NoLaunch) {
    Write-Host "Abriendo el panel para la prueba local..."
    Start-Process -FilePath $launcherPath -WorkingDirectory $projectRoot
} else {
    Write-Host "El panel no se abrio porque se uso -NoLaunch."
}
