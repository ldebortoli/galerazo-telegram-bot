function Get-DockerLinuxEngineReady {
    # Docker reports a stopped daemon on stderr; it is expected during startup.
    $ErrorActionPreference = "Continue"
    $engineType = & docker info --format "{{.OSType}}" 2>$null
    if ($LASTEXITCODE -ne 0) { return $false }
    if ($engineType -ne "linux") {
        throw "Docker usa '$engineType'; se requieren contenedores Linux. No se cambiara el motor automaticamente."
    }
    return $true
}

function Wait-DockerLinuxEngine {
    [CmdletBinding()]
    param([ValidateRange(0, 300)][int]$TimeoutSeconds = 180)

    if (Get-DockerLinuxEngineReady) { return }
    Write-Host "Docker Linux no esta disponible; iniciando Docker Desktop..." -ForegroundColor Cyan
    & docker desktop start --detach
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo iniciar Docker Desktop (codigo $LASTEXITCODE)."
    }
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        if (Get-DockerLinuxEngineReady) {
            Write-Host "Motor Docker Linux listo." -ForegroundColor Green
            return
        }
        if ([DateTime]::UtcNow -ge $deadline) { break }
        Start-Sleep -Seconds 2
    } while ($true)
    throw "Docker Desktop no habilito el motor Linux en $TimeoutSeconds segundos. El release se cancelo antes del build."
}
