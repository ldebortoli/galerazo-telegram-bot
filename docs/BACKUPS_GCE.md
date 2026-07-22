# Backups SQLite mensuales en Google Cloud

Este mecanismo crea una copia consistente de SQLite una vez por mes y la guarda fuera de la VM en un bucket privado de Cloud Storage. Es independiente del contenedor y se puede reutilizar para otros bots cambiando los parámetros.

## Diseño

- Un bucket compartido por proyecto: `gs://<project-id>-sqlite-backups`.
- Un prefijo aislado por bot: `bots/<bot-id>/AAAA/MM/`.
- Una copia local en la VM para recuperación rápida.
- `sqlite3.Connection.backup()` y `PRAGMA integrity_check` antes de subir.
- SHA-256 junto a cada archivo SQLite.
- Objetos de nombre inmutable; la subida falla si el nombre ya existe.
- Timer `systemd` mensual, persistente, con una demora aleatoria máxima de seis horas.
- Retención local y remota de 400 días, aproximadamente trece copias mensuales.
- Bucket con acceso uniforme y prevención de acceso público.
- La identidad de la VM recibe sólo `roles/storage.objectCreator` sobre el bucket; no puede leer, listar ni borrar backups.

El estado de la última copia válida queda en:

```text
<backup-dir>/last-backup-<bot-id>.json
```

No contiene secretos y puede ser consumido más adelante por Bot Control Center.

## Activar Galerazobot

La creación del bucket puede generar cargos si se superan las cuotas gratuitas, por lo que el script exige una confirmación explícita:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy\Enable-GceSqliteBackups.ps1 `
  -ProjectId bot-fleet-production `
  -Zone us-central1-a `
  -Instance galerazo-prod `
  -ServiceAccountName galerazo-vm `
  -BotId galerazobot `
  -AcknowledgePotentialStorageCost
```

La activación es idempotente y ejecuta inmediatamente una primera copia. Las siguientes se programan para el primer día de cada mes.

## Consultar o ejecutar manualmente

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy\Invoke-GceSqliteBackup.ps1 `
  -Action Status `
  -ProjectId bot-fleet-production `
  -Zone us-central1-a `
  -Instance galerazo-prod `
  -BotId galerazobot
```

Cambiar `Status` por `Run` crea otra copia en ese momento.

## Reutilizar con otro bot

Usar el mismo comando con otro `BotId`, VM, service account y rutas:

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

El bucket y su política se reutilizan; cada VM sólo agrega objetos nuevos bajo su prefijo.

## Restaurar una copia

La restauración es deliberadamente manual porque reemplaza producción:

1. Listar las copias:

   ```powershell
   gcloud storage ls "gs://bot-fleet-production-sqlite-backups/bots/galerazobot/**"
   ```

2. Descargar una SQLite elegida a `backups/`, que está ignorado por Git:

   ```powershell
   gcloud storage cp "gs://.../galerazobot-AAAAMMDDTHHMMSSZ-id.sqlite3" ".\backups\restore.sqlite3"
   ```

3. Verificar el SHA-256 descargado y ejecutar `PRAGMA integrity_check`.
4. Detener el bot remoto desde Bot Control Center y comprobar que no haya contenedores activos.
5. Reutilizar `Migrate-GceBotDatabase.ps1` indicando el archivo descargado y `-AcknowledgeDataMigration`.
6. Volver a desplegar la imagen elegida y verificar healthcheck, logs y comandos.

`MigrateData` crea además una copia de la base reemplazada y restaura automáticamente la anterior si la instalación falla.

## Comprobaciones operativas

- Revisar que el timer esté `enabled` y `active`.
- Alertar si `last-backup-<bot-id>.json` supera 40 días.
- Verificar periódicamente una copia descargada con `PRAGMA integrity_check`.
- No guardar bases, hashes descargados ni logs del servicio en Git.
