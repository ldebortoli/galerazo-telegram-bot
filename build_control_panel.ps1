$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$compiler = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$outputDirectory = Join-Path $projectRoot "bin"
$iconPng = Join-Path $projectRoot "assets\galerazo-bot-icon.png"
$iconIco = Join-Path $projectRoot "assets\galerazo-bot-icon.ico"

if (-not (Test-Path $compiler)) {
    throw "No se encontro el compilador de .NET Framework."
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
& "$projectRoot\scripts\build_windows_icon.ps1" -InputPath $iconPng -OutputPath $iconIco
& $compiler /nologo /target:winexe /win32icon:$iconIco /out:"$outputDirectory\GalerazoBotControl.exe" "$projectRoot\launcher\GalerazoBotControlLauncher.cs"

$appsDirectory = Join-Path (Split-Path -Parent $projectRoot) "CODEX APPS"
if (Test-Path -LiteralPath $appsDirectory) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $appsDirectory "Galerazo Bot.lnk"))
    $shortcut.TargetPath = Join-Path $outputDirectory "GalerazoBotControl.exe"
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.IconLocation = "$iconIco,0"
    $shortcut.Save()
}
