[CmdletBinding()]
param(
    [switch]$SkipShortcuts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$compilerCandidates = @(
    "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
    "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)
$compiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$outputDirectory = Join-Path $projectRoot "bin"
$launcherPath = Join-Path $outputDirectory "GalerazoBotControl.exe"
$iconPng = Join-Path $projectRoot "assets\galerazo-bot-icon.png"
$iconIco = Join-Path $projectRoot "assets\galerazo-bot-icon.ico"
$launcherSource = Join-Path $projectRoot "launcher\GalerazoBotControlLauncher.cs"

if (-not $compiler) {
    throw "No se encontro el compilador de .NET Framework incluido con Windows."
}
foreach ($requiredPath in @($iconPng, $launcherSource)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Falta un archivo requerido para compilar el panel: $requiredPath"
    }
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
& (Join-Path $projectRoot "scripts\build_windows_icon.ps1") `
    -InputPath $iconPng -OutputPath $iconIco
if (-not (Test-Path -LiteralPath $iconIco)) {
    throw "No se pudo generar el icono del panel."
}

& $compiler /nologo /target:winexe /win32icon:$iconIco `
    /out:$launcherPath $launcherSource
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $launcherPath)) {
    throw "No se pudo compilar GalerazoBotControl.exe."
}

function New-PanelShortcut {
    param([Parameter(Mandatory)][string]$ShortcutPath)

    $parent = Split-Path -Parent $ShortcutPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $null
    try {
        $shortcut = $shell.CreateShortcut($ShortcutPath)
        $shortcut.TargetPath = $launcherPath
        $shortcut.WorkingDirectory = $projectRoot
        $shortcut.IconLocation = "$iconIco,0"
        $shortcut.Description = "Configurar, encender y apagar Galerazo Bot"
        $shortcut.Save()
    } finally {
        if ($shortcut) {
            [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
        }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
    }
    Write-Host "Acceso directo creado: $ShortcutPath"
}

function New-LogsShortcut {
    param([Parameter(Mandatory)][string]$ShortcutPath)

    $logsScript = Join-Path $projectRoot "scripts\Watch-GceBotLogs.ps1"
    $powershellPath = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
    if (-not (Test-Path -LiteralPath $logsScript) -or -not (Test-Path -LiteralPath $powershellPath)) {
        throw "Falta el lanzador de logs o PowerShell de Windows."
    }

    $parent = Split-Path -Parent $ShortcutPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $null
    try {
        $shortcut = $shell.CreateShortcut($ShortcutPath)
        $shortcut.TargetPath = $powershellPath
        $shortcut.Arguments = "-NoExit -NoProfile -ExecutionPolicy Bypass -File `"$logsScript`""
        $shortcut.WorkingDirectory = $projectRoot
        $shortcut.IconLocation = "$iconIco,0"
        $shortcut.Description = "Ver logs remotos de Galerazo Bot"
        $shortcut.Save()
    } finally {
        if ($shortcut) {
            [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
        }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
    }
    Write-Host "Acceso directo creado: $ShortcutPath"
}

if (-not $SkipShortcuts) {
    $appsDirectory = Join-Path (Split-Path -Parent $projectRoot) "CODEX APPS"
    New-PanelShortcut -ShortcutPath (Join-Path $appsDirectory "Galerazo Bot.lnk")
    New-LogsShortcut -ShortcutPath (Join-Path $appsDirectory "Galerazo Bot - Logs.lnk")

    $desktop = [Environment]::GetFolderPath(
        [Environment+SpecialFolder]::DesktopDirectory
    )
    if ($desktop -and (Test-Path -LiteralPath $desktop)) {
        New-PanelShortcut -ShortcutPath (Join-Path $desktop "Galerazo Bot.lnk")
    } else {
        Write-Warning "No se encontro el Escritorio; se omitio ese acceso directo."
    }
}

Write-Host "Panel compilado: $launcherPath"
