[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$Region = "us-central1",
    [string]$Zone = "us-central1-a",
    [string]$Network = "bot-fleet",
    [string]$Subnet = "bots-us-central1",
    [string]$SubnetRange = "10.20.0.0/24",
    [string]$FirewallRule = "bot-fleet-allow-iap-ssh",
    [string]$Instance = "galerazo-prod",
    [string]$ServiceAccountId = "galerazo-vm",
    [string]$BotLabel = "galerazobot",
    [ValidateRange(10, 30)][int]$DiskSizeGB = 30,
    [switch]$AcknowledgeBillableResource
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-GcloudCommand {
    $command = Get-Command "gcloud" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $fallback = Join-Path $env:LOCALAPPDATA "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }

    throw "No se encontro gcloud. Instala Google Cloud CLI y ejecuta 'gcloud auth login'."
}

function Invoke-Gcloud {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$SuppressOutput
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        if ($SuppressOutput) {
            & $script:GcloudCommand @Arguments 1>$null 2>$null
            $result = $null
        }
        else {
            $result = & $script:GcloudCommand @Arguments 2>$null
        }
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($exitCode -ne 0) {
        throw "Fallo 'gcloud $($Arguments -join ' ')' con codigo $exitCode."
    }
    return $result
}

function Test-Gcloud {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $script:GcloudCommand @Arguments 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Get-GcloudJson {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $jsonArguments = $Arguments + @("--format=json")
    $json = Invoke-Gcloud -Arguments $jsonArguments
    return (($json -join [Environment]::NewLine) | ConvertFrom-Json)
}

function Test-PolicyBinding {
    param(
        [Parameter(Mandatory = $true)]$Policy,
        [Parameter(Mandatory = $true)][string]$Role,
        [Parameter(Mandatory = $true)][string]$Member
    )

    foreach ($binding in @($Policy.bindings)) {
        if ($binding.role -eq $Role -and $Member -in @($binding.members)) {
            return $true
        }
    }
    return $false
}

function Get-MetadataValue {
    param(
        [Parameter(Mandatory = $true)]$InstanceData,
        [Parameter(Mandatory = $true)][string]$Key
    )

    $item = @($InstanceData.metadata.items) | Where-Object { $_.key -eq $Key } | Select-Object -First 1
    return $item.value
}

function Get-ResourceName {
    param([string]$ResourceUrl)
    if (-not $ResourceUrl) {
        return ""
    }
    return ($ResourceUrl -split '/')[-1]
}

if (-not $AcknowledgeBillableResource) {
    throw "Crear una VM puede generar cargos. Reejecuta con -AcknowledgeBillableResource despues de revisar proyecto, region y Free Tier."
}

$resourcePattern = '^[a-z][a-z0-9-]{0,61}[a-z0-9]$'
foreach ($value in @($Network, $Subnet, $FirewallRule, $Instance, $BotLabel)) {
    if ($value -notmatch $resourcePattern) {
        throw "Nombre de recurso GCP invalido: $value"
    }
}
if ($ProjectId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') {
    throw "ProjectId invalido: $ProjectId"
}
if ($ServiceAccountId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') {
    throw "ServiceAccountId invalido: $ServiceAccountId"
}
if ($SubnetRange -notmatch '^10\.(?:[0-9]{1,3})\.(?:[0-9]{1,3})\.0/(?:2[0-8])$') {
    throw "SubnetRange debe ser un rango IPv4 privado 10.x.x.0 con prefijo /20 a /28."
}

$freeTierRegions = @("us-west1", "us-central1", "us-east1")
if ($Region -notin $freeTierRegions) {
    throw "La region '$Region' no esta en la lista de regiones elegibles configurada por el script."
}
if (-not $Zone.StartsWith("$Region-")) {
    throw "La zona '$Zone' no pertenece a la region '$Region'."
}

$script:GcloudCommand = Resolve-GcloudCommand
$configuredProject = (Invoke-Gcloud -Arguments @("config", "get-value", "project")).Trim()
if ($configuredProject -ne $ProjectId) {
    throw "El proyecto activo es '$configuredProject'. Ejecuta 'gcloud config set project $ProjectId' y reintenta."
}

$activeAccount = (Invoke-Gcloud -Arguments @("config", "get-value", "account")).Trim()
if (-not $activeAccount -or $activeAccount -eq "(unset)" -or $activeAccount -notmatch '@') {
    throw "No hay una cuenta activa en gcloud. Ejecuta 'gcloud auth login'."
}
$activeMemberKind = if ($activeAccount.EndsWith(".gserviceaccount.com")) { "serviceAccount" } else { "user" }
$activeMember = "${activeMemberKind}:$activeAccount"

$billingEnabled = (Invoke-Gcloud -Arguments @(
    "billing", "projects", "describe", $ProjectId,
    "--format=value(billingEnabled)"
)).Trim()
if ($billingEnabled -ne "True") {
    throw "El proyecto '$ProjectId' no tiene facturacion habilitada."
}

$serviceAccountEmail = "$ServiceAccountId@$ProjectId.iam.gserviceaccount.com"
if (-not (Test-Gcloud -Arguments @(
    "iam", "service-accounts", "describe", $serviceAccountEmail,
    "--project=$ProjectId"
))) {
    throw "No existe la service account '$ServiceAccountId'. Ejecuta Initialize-GcpBot.ps1 primero."
}

$networkExists = Test-Gcloud -Arguments @(
    "compute", "networks", "describe", $Network, "--project=$ProjectId"
)
if (-not $networkExists) {
    Invoke-Gcloud -Arguments @(
        "compute", "networks", "create", $Network,
        "--project=$ProjectId",
        "--subnet-mode=custom",
        "--bgp-routing-mode=regional",
        "--mtu=1460",
        "--quiet"
    ) -SuppressOutput
}
$networkData = Get-GcloudJson -Arguments @(
    "compute", "networks", "describe", $Network, "--project=$ProjectId"
)
if ($networkData.autoCreateSubnetworks -ne $false) {
    throw "La red '$Network' no es custom."
}

$subnetExists = Test-Gcloud -Arguments @(
    "compute", "networks", "subnets", "describe", $Subnet,
    "--region=$Region", "--project=$ProjectId"
)
if (-not $subnetExists) {
    Invoke-Gcloud -Arguments @(
        "compute", "networks", "subnets", "create", $Subnet,
        "--network=$Network",
        "--range=$SubnetRange",
        "--stack-type=IPV4_IPV6",
        "--ipv6-access-type=EXTERNAL",
        "--enable-private-ip-google-access",
        "--region=$Region",
        "--project=$ProjectId",
        "--quiet"
    ) -SuppressOutput
}
$subnetData = Get-GcloudJson -Arguments @(
    "compute", "networks", "subnets", "describe", $Subnet,
    "--region=$Region", "--project=$ProjectId"
)
$subnetProblems = @()
if ((Get-ResourceName $subnetData.network) -ne $Network) { $subnetProblems += "network" }
if ($subnetData.ipCidrRange -ne $SubnetRange) { $subnetProblems += "range" }
if ($subnetData.stackType -ne "IPV4_IPV6") { $subnetProblems += "stackType" }
if ($subnetData.ipv6AccessType -ne "EXTERNAL") { $subnetProblems += "ipv6AccessType" }
if ($subnetData.privateIpGoogleAccess -ne $true) { $subnetProblems += "privateGoogleAccess" }
if ($subnetProblems.Count -gt 0) {
    throw "La subred '$Subnet' no coincide con la configuracion esperada: $($subnetProblems -join ', ')."
}

$firewallExists = Test-Gcloud -Arguments @(
    "compute", "firewall-rules", "describe", $FirewallRule, "--project=$ProjectId"
)
if (-not $firewallExists) {
    Invoke-Gcloud -Arguments @(
        "compute", "firewall-rules", "create", $FirewallRule,
        "--network=$Network",
        "--direction=INGRESS",
        "--priority=1000",
        "--action=ALLOW",
        "--rules=tcp:22",
        "--source-ranges=35.235.240.0/20",
        "--target-tags=iap-ssh",
        "--project=$ProjectId",
        "--quiet"
    ) -SuppressOutput
}
$firewallData = Get-GcloudJson -Arguments @(
    "compute", "firewall-rules", "describe", $FirewallRule, "--project=$ProjectId"
)
$sshAllowed = @($firewallData.allowed) | Where-Object {
    $_.IPProtocol -eq "tcp" -and "22" -in @($_.ports)
}
if (
    (Get-ResourceName $firewallData.network) -ne $Network -or
    $firewallData.direction -ne "INGRESS" -or
    $firewallData.disabled -eq $true -or
    -not $sshAllowed -or
    "35.235.240.0/20" -notin @($firewallData.sourceRanges) -or
    "iap-ssh" -notin @($firewallData.targetTags)
) {
    throw "La regla '$FirewallRule' no coincide con SSH restringido a IAP."
}

foreach ($role in @("roles/iap.tunnelResourceAccessor", "roles/compute.osAdminLogin")) {
    Invoke-Gcloud -Arguments @(
        "projects", "add-iam-policy-binding", $ProjectId,
        "--member=$activeMember",
        "--role=$role",
        "--quiet"
    ) -SuppressOutput
}
Invoke-Gcloud -Arguments @(
    "iam", "service-accounts", "add-iam-policy-binding", $serviceAccountEmail,
    "--member=$activeMember",
    "--role=roles/iam.serviceAccountUser",
    "--project=$ProjectId",
    "--quiet"
) -SuppressOutput

$projectPolicy = Get-GcloudJson -Arguments @(
    "projects", "get-iam-policy", $ProjectId
)
$serviceAccountPolicy = Get-GcloudJson -Arguments @(
    "iam", "service-accounts", "get-iam-policy", $serviceAccountEmail,
    "--project=$ProjectId"
)
foreach ($role in @("roles/iap.tunnelResourceAccessor", "roles/compute.osAdminLogin")) {
    if (-not (Test-PolicyBinding -Policy $projectPolicy -Role $role -Member $activeMember)) {
        throw "No se pudo verificar el rol '$role' para el administrador activo."
    }
}
if (-not (Test-PolicyBinding -Policy $serviceAccountPolicy -Role "roles/iam.serviceAccountUser" -Member $activeMember)) {
    throw "No se pudo verificar Service Account User para el administrador activo."
}

$instanceExists = Test-Gcloud -Arguments @(
    "compute", "instances", "describe", $Instance,
    "--zone=$Zone", "--project=$ProjectId"
)
if (-not $instanceExists) {
    $networkInterface = "network=$Network,subnet=$Subnet,no-address,stack-type=IPV4_IPV6,ipv6-network-tier=PREMIUM"
    Invoke-Gcloud -Arguments @(
        "compute", "instances", "create", $Instance,
        "--zone=$Zone",
        "--project=$ProjectId",
        "--machine-type=e2-micro",
        "--provisioning-model=STANDARD",
        "--maintenance-policy=MIGRATE",
        "--network-interface=$networkInterface",
        "--image-family=debian-12",
        "--image-project=debian-cloud",
        "--boot-disk-type=pd-standard",
        "--boot-disk-size=${DiskSizeGB}GB",
        "--service-account=$serviceAccountEmail",
        "--scopes=https://www.googleapis.com/auth/cloud-platform",
        "--metadata=enable-oslogin=TRUE,block-project-ssh-keys=TRUE",
        "--tags=iap-ssh",
        "--labels=app=$BotLabel,environment=production,managed-by=galerazo-deploy",
        "--shielded-secure-boot",
        "--shielded-vtpm",
        "--shielded-integrity-monitoring",
        "--deletion-protection",
        "--quiet"
    ) -SuppressOutput
}

$instanceData = Get-GcloudJson -Arguments @(
    "compute", "instances", "describe", $Instance,
    "--zone=$Zone", "--project=$ProjectId"
)
$interface = @($instanceData.networkInterfaces)[0]
$ipv4AccessConfigsProperty = $interface.PSObject.Properties["accessConfigs"]
$ipv4AccessConfigs = @()
if ($ipv4AccessConfigsProperty) {
    $ipv4AccessConfigs = @($ipv4AccessConfigsProperty.Value)
}
$ipv6AccessConfigsProperty = $interface.PSObject.Properties["ipv6AccessConfigs"]
$ipv6AccessConfigs = @()
if ($ipv6AccessConfigsProperty) {
    $ipv6AccessConfigs = @($ipv6AccessConfigsProperty.Value)
}
$bootDiskName = Get-ResourceName (@($instanceData.disks)[0].source)
$diskData = Get-GcloudJson -Arguments @(
    "compute", "disks", "describe", $bootDiskName,
    "--zone=$Zone", "--project=$ProjectId"
)
$instanceProblems = @()
if ((Get-ResourceName $instanceData.machineType) -ne "e2-micro") { $instanceProblems += "machineType" }
if ((Get-ResourceName $interface.subnetwork) -ne $Subnet) { $instanceProblems += "subnet" }
if ($interface.stackType -ne "IPV4_IPV6") { $instanceProblems += "stackType" }
if ($ipv4AccessConfigs.Count -ne 0) { $instanceProblems += "externalIPv4" }
if ($ipv6AccessConfigs.Count -eq 0 -or -not $ipv6AccessConfigs[0].externalIpv6) { $instanceProblems += "externalIPv6" }
if (@($instanceData.serviceAccounts)[0].email -ne $serviceAccountEmail) { $instanceProblems += "serviceAccount" }
if ((Get-ResourceName $diskData.type) -ne "pd-standard") { $instanceProblems += "diskType" }
if ([int]$diskData.sizeGb -ne $DiskSizeGB) { $instanceProblems += "diskSize" }
if ($instanceData.deletionProtection -ne $true) { $instanceProblems += "deletionProtection" }
if ($instanceData.shieldedInstanceConfig.enableSecureBoot -ne $true) { $instanceProblems += "secureBoot" }
if ($instanceData.shieldedInstanceConfig.enableVtpm -ne $true) { $instanceProblems += "vTPM" }
if ($instanceData.shieldedInstanceConfig.enableIntegrityMonitoring -ne $true) { $instanceProblems += "integrityMonitoring" }
if ((Get-MetadataValue -InstanceData $instanceData -Key "enable-oslogin") -ne "TRUE") { $instanceProblems += "osLogin" }
if ((Get-MetadataValue -InstanceData $instanceData -Key "block-project-ssh-keys") -ne "TRUE") { $instanceProblems += "projectSshKeys" }
if ("iap-ssh" -notin @($instanceData.tags.items)) { $instanceProblems += "iapTag" }
if ($instanceProblems.Count -gt 0) {
    throw "La VM '$Instance' no coincide con la configuracion esperada: $($instanceProblems -join ', ')."
}

Write-Host "Infraestructura GCE lista." -ForegroundColor Green
Write-Host "Red/subred: $Network / $Subnet ($SubnetRange, dual-stack externo)" -ForegroundColor DarkGray
Write-Host "SSH: solo IAP hacia tcp:22" -ForegroundColor DarkGray
Write-Host "VM: $Instance, e2-micro, ${DiskSizeGB}GB pd-standard, Debian 12" -ForegroundColor DarkGray
Write-Host "IPv4 externa: ninguna" -ForegroundColor DarkGray
Write-Host "IPv6 externa: efimera" -ForegroundColor DarkGray
Write-Host "Protecciones: OS Login, Shielded VM y deletion protection" -ForegroundColor DarkGray
Write-Host "El bot todavia no fue desplegado." -ForegroundColor DarkGray
