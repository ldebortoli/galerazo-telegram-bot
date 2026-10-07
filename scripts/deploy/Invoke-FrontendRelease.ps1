[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet("sync", "verify")][string]$Stage,
    [Parameter(Mandatory = $true)][string]$FrontendRepositoryPath,
    [Parameter(Mandatory = $true)][string]$RuntimeRepositoryPath,
    [Parameter(Mandatory = $true)][string]$BotSourceRoot,
    [Parameter(Mandatory = $true)][string]$ResultFile,
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Zone,
    [Parameter(Mandatory = $true)][string]$Instance,
    [string]$ExpectedImage
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$python = Join-Path $RuntimeRepositoryPath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Falta .venv del checkout de Galerazo." }
$expectedPython = (Get-Content -LiteralPath (Join-Path $BotSourceRoot ".python-version") -Raw).Trim()
$actualPython = (& $python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
if ($LASTEXITCODE -ne 0 -or $actualPython -ne $expectedPython) { throw "Runtime Python desalineado para integrar frontend." }
$versionSource = Get-Content -LiteralPath (Join-Path $BotSourceRoot "galerazo_bot\versioning.py") -Raw
if ($versionSource -notmatch 'CURRENT_VERSION\s*=\s*"([0-9.]+)"') { throw "Version del bot no disponible." }
$targetVersion = $Matches[1]
$arguments = @(
    (Join-Path $BotSourceRoot "scripts\frontend_release.py"),
    "--stage", $Stage, "--repository", $FrontendRepositoryPath,
    "--project", $ProjectId, "--zone", $Zone, "--instance", $Instance,
    "--result", $ResultFile, "--target-bot-version", $targetVersion
)
if ($ExpectedImage) { $arguments += @("--expected-image", $ExpectedImage) }
$env:WRANGLER_WRITE_LOGS = "false"
$env:WRANGLER_SEND_METRICS = "false"
$env:MINIFLARE_REGISTRY_PATH = Join-Path ([System.IO.Path]::GetTempPath()) "galerazo-miniflare-registry"
& $python @arguments
if ($LASTEXITCODE -ne 0) { throw "Fallo de integracion frontend ($Stage); el release no puede marcarse exitoso." }
