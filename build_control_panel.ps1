$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$compiler = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$outputDirectory = Join-Path $projectRoot "bin"

if (-not (Test-Path $compiler)) {
    throw "No se encontro el compilador de .NET Framework."
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
& $compiler /nologo /target:winexe /win32icon:"$projectRoot\assets\galerazo-bot-icon.ico" /out:"$outputDirectory\GalerazoBotControl.exe" "$projectRoot\launcher\GalerazoBotControlLauncher.cs"
