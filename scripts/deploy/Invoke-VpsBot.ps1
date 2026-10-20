[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$VpsConfigFile,
    [Parameter(Mandatory=$true)][ValidateSet('publish','deploy','rollback','credential-status','credentials','status','triggers','media','moderate','stop','notify-release')][string]$Action,
    [string]$Image,[string]$Tag,[string]$PatchFile,[string]$OutputFile,
    [ValidatePattern('^[A-Za-z0-9_-]{1,2048}$')][string]$TriggerId,
    [ValidateSet('delete-trigger','block-user','delete-and-block')][string]$ModerationAction,
    [ValidateSet('started','succeeded','failed','skipped')][string]$ReleaseEvent,
    [ValidateLength(1,800)][string]$ReleaseDetail,
    [switch]$AcknowledgeModeration,[switch]$AcknowledgeStop,[switch]$AcknowledgeSecretUpdate
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python=Join-Path $projectRoot '.venv/Scripts/python.exe'
if(-not(Test-Path -LiteralPath $python)) { $python=(Get-Command py -ErrorAction Stop).Source; $prefix=@('-3.14') } else { $prefix=@() }
if($Action -eq 'moderate' -and (-not $AcknowledgeModeration -or -not $TriggerId -or -not $ModerationAction)){throw 'Moderacion requiere confirmacion, trigger y accion.'}
if($Action -eq 'stop' -and -not $AcknowledgeStop){throw 'Detencion requiere confirmacion.'}
if($Action -eq 'credentials' -and (-not $AcknowledgeSecretUpdate -or -not $PatchFile)){throw 'Parche requiere confirmacion y archivo privado.'}
if($Action -eq 'media' -and (-not $TriggerId -or -not $OutputFile)){throw 'Multimedia requiere trigger y archivo de salida.'}
if($Action -eq 'notify-release' -and (-not $ReleaseEvent -or ($ReleaseEvent -eq 'failed' -and -not $ReleaseDetail) -or ($ReleaseEvent -ne 'failed' -and $ReleaseDetail))){throw 'Notificacion de release invalida.'}
$arguments=@($prefix)+@('-X','utf8',(Join-Path $projectRoot 'scripts/vps_operations.py'),'--root',$projectRoot,'--config',$VpsConfigFile,'--action',$Action)
foreach($pair in @(@('--image',$Image),@('--tag',$Tag),@('--patch',$PatchFile),@('--output',$OutputFile))){if($pair[1]){$arguments+=$pair}}
if($Action -in @('media','moderate')){$arguments+=@('--',$TriggerId);if($Action -eq 'moderate'){$arguments+=$ModerationAction}}
if($Action -eq 'notify-release'){$arguments+=@('--',$ReleaseEvent);if($ReleaseDetail){$arguments+=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($ReleaseDetail))}}
& $python @arguments
if($LASTEXITCODE -ne 0){throw "La operacion VPS fallo ($Action)."}
