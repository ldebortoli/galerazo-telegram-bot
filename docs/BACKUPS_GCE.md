# Backups SQLite mensuales en Google Cloud

Este documento es el runbook operativo y reproducible de los backups externos de
SQLite para Galerazobot y los futuros bots de la misma flota. El mecanismo crea
una copia consistente una vez por mes, la valida y la guarda fuera de la VM en
un bucket privado de Cloud Storage.

No depende del contenedor, no reinicia el bot y no incorpora la base a la imagen
Docker. Un deploy nuevo tampoco sobrescribe estas copias.

## Resumen ejecutivo

| Tema | Decisión actual |
| --- | --- |
| Frecuencia | Mensual, al comienzo del mes, con demora aleatoria de hasta seis horas. |
| Fuente | SQLite activa en el disco persistente de la VM. |
| Consistencia | API `sqlite3.Connection.backup()`, apta para copiar mientras el bot está escribiendo. |
| Verificación | `PRAGMA integrity_check`, tamaño informado por GCS y SHA-256. |
| Destino remoto | Bucket privado compartido por proyecto, prefijo lógico por bot. |
| Retención | 400 días en la VM y en Cloud Storage, aproximadamente trece ejecuciones. |
| Autenticación | Identidad adjunta a la VM; no hay claves JSON ni tokens persistidos. |
| Restauración | Manual y confirmada, porque reemplaza datos de producción. |
| Bot Control Center | Puede leer el estado y disparar el script versionado; no necesita comandos SSH libres. |

Estado instalado de Galerazobot al 22 de julio de 2026:

| Recurso | Valor |
| --- | --- |
| Proyecto | `bot-fleet-production` |
| VM | `galerazo-prod`, zona `us-central1-a` |
| Identidad | `galerazo-vm@bot-fleet-production.iam.gserviceaccount.com` |
| Bucket | `gs://bot-fleet-production-sqlite-backups` |
| Prefijo | `bots/galerazobot/` |
| SQLite | `/srv/galerazo/data/galerazo.sqlite3` |
| Copias locales | `/srv/galerazo/backups/monthly` |
| Timer | `bot-fleet-sqlite-backup-galerazobot.timer` |
| Próxima ejecución comprobada | 1 de agosto de 2026, 05:15:50 UTC (02:15:50 de Argentina) |
| Primera copia comprobada | 180224 bytes, SHA-256 e integridad correctos |

## Qué problema resuelve

Hay tres tipos distintos de copia en el proyecto y no deben confundirse:

1. `/backup` crea una copia local solicitada por un dev y trata de enviarla por
   Telegram.
2. El deploy crea una copia local antes de reemplazar la versión o la base para
   poder hacer rollback inmediato.
3. Este mecanismo mensual crea una copia externa en Cloud Storage. Sobrevive a
   la pérdida de la VM o de su disco.

Los dos primeros mecanismos son útiles para errores de aplicación o de deploy,
pero no protegen por sí solos contra la pérdida completa de la VM.

## Arquitectura

```text
galerazo-prod
  /srv/galerazo/data/galerazo.sqlite3
                |
                | sqlite3.Connection.backup()
                v
  /srv/galerazo/backups/monthly/*.sqlite3
                |
                | integrity_check + SHA-256
                | token efímero del Metadata Server
                v
gs://bot-fleet-production-sqlite-backups/
  bots/galerazobot/AAAA/MM/*.sqlite3
  bots/galerazobot/AAAA/MM/*.sqlite3.sha256
```

### Componentes versionados

| Archivo | Responsabilidad |
| --- | --- |
| `deploy/gce/sqlite_backup.py` | Crea, valida, firma y sube una copia. |
| `deploy/gce/install-sqlite-backup.sh` | Instala usuario, configuración y unidades `systemd`. |
| `deploy/gce/backup-lifecycle.json` | Define la eliminación remota después de 400 días. |
| `scripts/deploy/Enable-GceSqliteBackups.ps1` | Prepara GCS/IAM, instala el runtime y ejecuta la primera copia. |
| `scripts/deploy/Invoke-GceSqliteBackup.ps1` | Consulta estado o dispara una copia mediante IAP. |
| `tests/test_sqlite_backup.py` | Prueba consistencia, integridad, retención y controles de seguridad. |

### Recursos instalados en cada VM

| Recurso | Ubicación o nombre |
| --- | --- |
| Runtime genérico | `/usr/local/lib/bot-fleet-backup/sqlite_backup.py` |
| Configuración por bot | `/etc/bot-fleet-backup/<bot-id>.json` |
| Servicio | `bot-fleet-sqlite-backup-<bot-id>.service` |
| Timer | `bot-fleet-sqlite-backup-<bot-id>.timer` |
| Estado exitoso más reciente | `<backup-dir>/last-backup-<bot-id>.json` |

La configuración queda `root:<runtime-gid>/0640`, el directorio local queda
`0700` y cada SQLite/hash queda `0600`. Si el UID del contenedor no tiene una
cuenta equivalente en el host, el instalador crea un usuario sin login y sin
home para que `systemd` pueda ejecutar el servicio con ese UID.

## Secuencia exacta de una ejecución

1. `systemd` inicia el servicio como el UID/GID que ya puede leer la SQLite.
2. El runtime abre la base de origen en modo de solo lectura y espera hasta 30
   segundos si SQLite está ocupada.
3. `Connection.backup()` escribe un archivo `.partial` dentro del directorio de
   backups. No se copian directamente `-wal` ni `-shm`.
4. Ejecuta `PRAGMA integrity_check` sobre la copia, cambia el modo a `0600` y
   recién entonces la renombra como copia terminada.
5. Calcula SHA-256 y crea el archivo compañero `.sqlite3.sha256`.
6. Solicita un access token efímero al Metadata Server de GCE.
7. Sube primero la SQLite y después el hash por HTTPS a Cloud Storage.
8. Cada alta usa `ifGenerationMatch=0`: un objeto existente nunca se
   sobrescribe.
9. Compara el tamaño local con el tamaño devuelto por Cloud Storage.
10. Después de que ambas subidas terminan, elimina copias locales del mismo bot
    con más de 400 días y escribe atómicamente el JSON de estado.

Si cualquier paso falla, el servicio termina con error y el JSON de último
éxito no se actualiza. Un fallo después de subir la SQLite y antes de subir el
hash puede dejar un objeto huérfano; no se considera exitoso y la regla de ciclo
de vida lo eliminará eventualmente. La siguiente ejecución usa timestamp y
UUID nuevos, por lo que puede reintentarse sin sobrescribir nada.

## Programación y retención

El timer usa:

```ini
OnCalendar=monthly
Persistent=true
RandomizedDelaySec=6h
AccuracySec=1h
```

- `monthly` programa una ejecución al comienzo de cada mes.
- La demora aleatoria evita que todos los bots copien al mismo instante.
- `Persistent=true` hace que una ejecución perdida por VM apagada se recupere
  al volver a encenderla.
- `Status` muestra el próximo horario efectivo calculado por `systemd`.

La retención local se aplica después de una subida exitosa. Cloud Storage usa
una regla de ciclo de vida sobre `bots/` y procesa de manera asíncrona los
objetos con más de 400 días. El bucket también conserva durante siete días los
objetos borrados mediante su política de soft delete actual.

Con una ejecución mensual se conservan normalmente unas trece copias, no sólo
doce, porque 400 días cubren algo más de un año.

## Nombres y organización

Formato remoto:

```text
bots/<bot-id>/<AAAA>/<MM>/<bot-id>-<AAAAMMDDTHHMMSSZ>-<uuid8>.sqlite3
bots/<bot-id>/<AAAA>/<MM>/<bot-id>-<AAAAMMDDTHHMMSSZ>-<uuid8>.sqlite3.sha256
```

Ejemplo real:

```text
bots/galerazobot/2026/07/galerazobot-20260722T050358Z-2b094c8a.sqlite3
```

`BotId` debe comenzar con letra o número, usar sólo minúsculas, números y
guiones, y tener como máximo 63 caracteres.

## Modelo de seguridad

- El bucket usa acceso uniforme y prevención de acceso público.
- No se crean URLs públicas ni claves de service account.
- El token de GCS se obtiene en memoria desde el Metadata Server y expira.
- La identidad de la VM recibe `roles/storage.objectCreator` sólo sobre el
  bucket, no `storage.admin` ni permisos a nivel proyecto.
- Esa identidad puede crear objetos, pero no leer, listar, borrar ni
  sobrescribir backups existentes.
- El servicio `systemd` usa endurecimiento: filesystem del sistema protegido,
  dispositivos y homes privados, sin privilegios nuevos, sin namespaces ni
  capacidades de administración del kernel.
- La base se abre de sólo lectura y el servicio sólo puede escribir en su
  directorio de backups.

### Límite del aislamiento en un bucket compartido

`bots/<bot-id>/` es una separación lógica, no una frontera IAM. Como
`storage.objectCreator` se concede sobre el bucket, una VM comprometida podría
crear un objeto nuevo bajo el prefijo de otro bot, aunque no podría leer,
sobrescribir ni borrar ninguno. El UUID aleatorio hace además impráctico
adivinar el nombre exacto de una futura copia.

El bucket compartido es apropiado para bots personales bajo el mismo dueño y
nivel de confianza. Para bots de clientes, equipos distintos o datos que
requieran aislamiento fuerte, usar otro bucket o directamente otro proyecto y
cuenta de facturación.

## Costos y capacidad

El mecanismo no crea otra VM: usa unos segundos de CPU y red de la VM existente
una vez por mes. Cada ejecución genera dos objetos, la SQLite y su hash.

Estimación simple por bot:

```text
almacenamiento estable aproximado = tamaño medio de SQLite × 13
operaciones de creación aproximadas = 2 × ejecuciones mensuales
```

Con la primera base de Galerazobot, de 180224 bytes, trece SQLite ocuparían
aproximadamente 2,2 MiB más hashes. El valor crecerá con la base y puede aumentar
temporalmente por soft delete. Descargar una copia para restaurarla también
puede implicar transferencia según origen, región y precios vigentes.

No se promete costo cero. `Enable-GceSqliteBackups.ps1` exige
`-AcknowledgePotentialStorageCost`, el presupuesto de Google Cloud sólo alerta
y no detiene recursos, y los precios/cuotas deben revisarse en la documentación
oficial antes de ampliar frecuencia, retención o cantidad de bots.

## Requisitos previos

- Google Cloud CLI instalado y autenticado con permisos para habilitar APIs,
  administrar el bucket y modificar su IAM.
- Proyecto con facturación habilitada.
- VM accesible por SSH mediante IAP.
- Service account adjunta a la VM.
- Python 3 disponible en el host.
- SQLite existente en una ruta absoluta y regular, no symlink.
- UID de runtime entre 1 y 60000 con permiso de lectura sobre la base.
- Región del bucket aceptada por el script: `us-west1`, `us-central1` o
  `us-east1`.

## Qué hace el habilitador

`Enable-GceSqliteBackups.ps1` es idempotente y realiza estas acciones:

1. Valida nombres, rutas, UID y confirmación de posible costo.
2. Habilita `storage.googleapis.com`.
3. Crea `gs://<project-id>-sqlite-backups` si todavía no existe.
4. Fuerza acceso uniforme, prevención de acceso público y ciclo de vida de 400
   días.
5. Agrega `roles/storage.objectCreator` para la identidad de la VM.
6. Copia el runtime y el instalador por IAP.
7. Instala o actualiza configuración, servicio y timer.
8. Habilita el timer y ejecuta inmediatamente una primera copia.
9. Lista los objetos del bot usando la identidad humana local como comprobación.

No detiene el contenedor, no cambia la SQLite, no lee secretos de Telegram y no
publica una imagen Docker.

### Parámetros

| Parámetro | Obligatorio | Default | Significado |
| --- | --- | --- | --- |
| `ProjectId` | Sí | — | Proyecto que contiene VM y bucket. |
| `Zone` | Sí | — | Zona de la VM. |
| `Instance` | Sí | — | Nombre de la VM. |
| `ServiceAccountName` | Sí | — | Nombre corto de la identidad adjunta. |
| `BotId` | Sí | — | Identificador estable usado en unidades, estado y prefijo. |
| `Location` | No | `us-central1` | Región del bucket. |
| `BucketName` | No | `<project-id>-sqlite-backups` | Permite usar otro bucket. |
| `DatabasePath` | No | `/srv/galerazo/data/galerazo.sqlite3` | SQLite remota. |
| `BackupDirectory` | No | `/srv/galerazo/backups/monthly` | Retención local y estado. |
| `RuntimeUid` | No | `10001` | UID/GID que puede leer la SQLite. |
| `AcknowledgePotentialStorageCost` | Sí | falso | Confirmación explícita de posible costo. |

## Activar Galerazobot

Desde la raíz del repositorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy\Enable-GceSqliteBackups.ps1 `
  -ProjectId bot-fleet-production `
  -Zone us-central1-a `
  -Instance galerazo-prod `
  -ServiceAccountName galerazo-vm `
  -BotId galerazobot `
  -AcknowledgePotentialStorageCost
```

Puede reejecutarse después de actualizar los scripts: conserva el bucket y los
objetos existentes, vuelve a aplicar su configuración y ejecuta una copia nueva.

## Reutilizarlo con otro bot

Se comparte el código y, para bots personales, también el bucket. Cambiar VM,
identidad, `BotId` y rutas:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy\Enable-GceSqliteBackups.ps1 `
  -ProjectId bot-fleet-production `
  -Zone us-central1-a `
  -Instance otro-bot-prod `
  -ServiceAccountName otro-bot-vm `
  -BotId otro-bot `
  -DatabasePath /srv/otro-bot/data/bot.sqlite3 `
  -BackupDirectory /srv/otro-bot/backups/monthly `
  -RuntimeUid 10001 `
  -AcknowledgePotentialStorageCost
```

Checklist para cada bot nuevo:

1. Confirmar que `BotId` no cambiará con las releases.
2. Confirmar la ruta real de SQLite dentro del host, no la del contenedor.
3. Confirmar UID/GID y permisos con los que corre el contenedor.
4. Usar una service account propia para esa VM.
5. Ejecutar el habilitador y comprobar la primera copia.
6. Descargar esa primera copia, validar hash e integridad.
7. Registrar el bot en Bot Control Center con los mismos identificadores.
8. Crear alerta si el último éxito supera 40 días.

Para un cliente o un dominio de confianza diferente, indicar además un
`BucketName` exclusivo o separar el proyecto completo.

## Consultar estado

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy\Invoke-GceSqliteBackup.ps1 `
  -Action Status `
  -ProjectId bot-fleet-production `
  -Zone us-central1-a `
  -Instance galerazo-prod `
  -BotId galerazobot
```

La salida, en este orden, indica:

1. `enabled`: el timer inicia también después de reiniciar la VM.
2. `active`: el timer está esperando su próxima fecha.
3. Próxima ejecución calculada por `systemd`.
4. `Result` de la última ejecución del servicio.
5. Últimas cuatro líneas del journal del servicio.

El JSON de estado sólo representa una ejecución completamente exitosa:

```json
{
  "botId": "galerazobot",
  "completedAt": "2026-07-22T05:03:58.051393Z",
  "integrity": "ok",
  "localPath": "/srv/galerazo/backups/monthly/galerazobot-20260722T050358Z-2b094c8a.sqlite3",
  "objectUri": "gs://bot-fleet-production-sqlite-backups/bots/galerazobot/2026/07/galerazobot-20260722T050358Z-2b094c8a.sqlite3",
  "sha256": "bd6d282708e47dc5cef9d58982c574f1d312c3ec71aa98097e8102ae71b5cf37",
  "sizeBytes": 180224
}
```

Bot Control Center puede mostrar estos campos y considerar atrasado el backup
si `completedAt` tiene más de 40 días. No necesita leer la SQLite ni credenciales.

## Ejecutar una copia manual

Cambiar `Status` por `Run`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy\Invoke-GceSqliteBackup.ps1 `
  -Action Run `
  -ProjectId bot-fleet-production `
  -Zone us-central1-a `
  -Instance galerazo-prod `
  -BotId galerazobot
```

Esto no modifica el calendario mensual. Es útil antes de una migración riesgosa
o para comprobar el mecanismo después de cambiar permisos.

## Comprobaciones directas en Google Cloud

Listar copias con la cuenta administradora local:

```powershell
gcloud storage ls "gs://bot-fleet-production-sqlite-backups/bots/galerazobot/**"
```

Revisar configuración del bucket:

```powershell
gcloud storage buckets describe gs://bot-fleet-production-sqlite-backups
gcloud storage buckets get-iam-policy gs://bot-fleet-production-sqlite-backups
```

La identidad de la VM no debe tener permisos para ejecutar esas lecturas. Que
fallen desde la VM con `403` es parte del diseño; sólo la subida de objetos
nuevos debe estar autorizada.

## Restaurar una copia

Restaurar reemplaza producción. Hacerlo sólo con una copia seleccionada y una
ventana de mantenimiento.

### 1. Elegir y descargar el par

```powershell
gcloud storage ls "gs://bot-fleet-production-sqlite-backups/bots/galerazobot/**"
gcloud storage cp "gs://.../copia.sqlite3" ".\backups\restore.sqlite3"
gcloud storage cp "gs://.../copia.sqlite3.sha256" ".\backups\restore.sqlite3.sha256"
```

`backups/` está ignorado por Git. No copiar ninguno de estos archivos al
repositorio.

### 2. Verificar SHA-256

```powershell
$expected = ((Get-Content .\backups\restore.sqlite3.sha256).Trim() -split '\s+')[0].ToLowerInvariant()
$actual = (Get-FileHash .\backups\restore.sqlite3 -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "El SHA-256 no coincide." }
```

### 3. Verificar SQLite

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3,sys; c=sqlite3.connect(f'file:{sys.argv[1]}?mode=ro', uri=True); print(c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()" .\backups\restore.sqlite3
```

La salida debe ser exactamente `ok`.

### 4. Detener y comprobar

1. Detener Galerazobot desde Bot Control Center.
2. Confirmar que el contenedor remoto no está activo.
3. Confirmar que no corre localmente otro bot con el mismo token.
4. Crear, si es posible, una última copia manual del estado que se va a
   reemplazar.

### 5. Migrar la copia validada

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy\Migrate-GceBotDatabase.ps1 `
  -ProjectId bot-fleet-production `
  -Zone us-central1-a `
  -Instance galerazo-prod `
  -DatabaseFile .\backups\restore.sqlite3 `
  -AcknowledgeDataMigration
```

El migrador vuelve a crear una copia consistente local, valida integridad,
transfiere por IAP mediante temporales privados, respalda la base remota previa
y la restaura automáticamente si la instalación falla.

### 6. Volver a iniciar y validar

1. Desplegar o iniciar la imagen elegida.
2. Esperar `running/healthy`.
3. Revisar logs, reinicios y `PRAGMA integrity_check` remoto.
4. Probar `/hola`, `/nivel` y un comando que lea datos restaurados.
5. Ejecutar una copia mensual manual para establecer un nuevo punto posterior a
   la restauración.

## Pausar, reactivar o retirar un bot

Pausar sin borrar configuración ni copias:

```powershell
gcloud compute ssh galerazo-prod --project=bot-fleet-production --zone=us-central1-a --tunnel-through-iap --command="sudo systemctl disable --now bot-fleet-sqlite-backup-galerazobot.timer"
```

Reactivar:

```powershell
gcloud compute ssh galerazo-prod --project=bot-fleet-production --zone=us-central1-a --tunnel-through-iap --command="sudo systemctl enable --now bot-fleet-sqlite-backup-galerazobot.timer"
```

Al retirar definitivamente una VM, quitar su binding de
`roles/storage.objectCreator`. No borrar inmediatamente las copias: conservarlas
hasta que venza el período de recuperación acordado o dejar actuar la regla de
400 días.

## Diagnóstico de fallos

Consultar primero:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy\Invoke-GceSqliteBackup.ps1 `
  -Action Status `
  -ProjectId bot-fleet-production `
  -Zone us-central1-a `
  -Instance galerazo-prod `
  -BotId galerazobot
```

Para más journal:

```powershell
gcloud compute ssh galerazo-prod --project=bot-fleet-production --zone=us-central1-a --tunnel-through-iap --command="sudo journalctl -u bot-fleet-sqlite-backup-galerazobot.service --no-pager -n 100"
```

| Síntoma | Causa probable | Acción |
| --- | --- | --- |
| `217/USER` | El UID no tiene cuenta válida en el host. | Reejecutar el habilitador actual; crea una cuenta sin login para ese UID. |
| `ConditionPathExists` o base inexistente | `DatabasePath` incorrecto o disco sin montar. | Verificar la ruta host y reejecutar con el parámetro correcto. |
| `PermissionError` local | UID/GID no puede leer SQLite o escribir backups. | Revisar owner/modos y `RuntimeUid`; no abrir permisos globalmente. |
| `Metadata token request failed` | La VM no accede al Metadata Server o no tiene identidad adjunta. | Revisar service account de la instancia y red local. |
| GCS `403` al subir | Falta API, scope o `storage.objectCreator` para la identidad real. | Comparar service account adjunta con `ServiceAccountName` y reejecutar el habilitador. |
| GCS `412` | Ya existe el nombre inmutable. | No sobrescribir; ejecutar otra vez para generar timestamp/UUID nuevos. |
| `integrity_check` falla | La copia no es recuperable. | No restaurarla; conservar logs y seleccionar otra copia. |
| Tamaño inesperado | GCS no confirmó el mismo tamaño local. | Tratar la ejecución como fallida y reintentar después de revisar red/GCS. |
| Timer `inactive` o `disabled` | Fue pausado o la instalación quedó incompleta. | Reejecutar el habilitador o `systemctl enable --now`. |
| Estado con más de 40 días | No hubo éxito reciente aunque el timer pueda seguir activo. | Revisar `Result`, journal, IAM, espacio en disco y ejecutar `Run`. |
| SSH/IAP falla | Sesión, permisos IAP/OS Login, zona o VM incorrectos. | Probar `gcloud compute ssh ... --troubleshoot --tunnel-through-iap`. |

Nunca imprimir `/etc/bot-fleet-backup/*.json` junto con otros archivos de
configuración del bot ni copiar `.env`, bases o logs al repositorio.

## Rutina operativa recomendada

### Mensual o automatizada en Bot Control Center

- Timer `enabled` y `active`.
- Último `Result=success`.
- `completedAt` menor a 40 días.
- `integrity=ok` y `sizeBytes > 0`.
- El objeto nuevo aparece bajo el prefijo esperado.

### Cada seis meses o antes de depender de estos datos

- Descargar una copia elegida y su hash.
- Validar SHA-256 e `integrity_check` fuera de la VM.
- Ensayar la restauración en una SQLite temporal o VM de prueba.
- Confirmar que la cuenta administradora puede leer, pero la VM no.
- Revisar precios, tamaño acumulado, lifecycle, soft delete y presupuesto.

### Después de cambios de infraestructura

Reejecutar el habilitador si cambia alguno de estos datos:

- ruta de SQLite o directorio de backups;
- UID/GID del runtime;
- nombre de VM, service account, proyecto, región o bucket;
- `BotId` estable del servicio.

Un cambio normal de código o imagen Docker no requiere reinstalar backups.

## Criterio de éxito para un bot nuevo

La instalación no se considera terminada hasta comprobar todo esto:

- primera ejecución `success`;
- timer `enabled` y `active`;
- próxima fecha visible;
- SQLite y `.sha256` presentes en GCS;
- copia descargada con hash coincidente;
- `PRAGMA integrity_check` devuelve `ok` sobre la descarga;
- bot original sigue `running/healthy` y sin reinicios nuevos;
- configuración y bases no aparecen en `git status`.
