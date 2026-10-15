[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance,
    [string]$Location = "us-central1",
    [string]$Repository = "bots",
    [string]$CandidateImage
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = Join-Path $projectRoot ".venv/bin/python"
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Falta el entorno .venv del proyecto para proteger el registro."
}
$tool = Join-Path $projectRoot "scripts\registry_retention.py"
$arguments = @($tool, "--project", $ProjectId, "--zone", $Zone, "--instance", $Instance,
    "--location", $Location, "--repository", $Repository, "--apply")
if ($CandidateImage) {
    $arguments += @("--candidate", $CandidateImage)
}
& $python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo verificar la retencion del registro; no continuar con otra publicacion o deploy."
}
