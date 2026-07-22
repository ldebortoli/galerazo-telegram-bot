# Session handoff

## Objetivo general

Mantener Galerazo Bot reproducible en Windows, CI y Docker, con SQLite persistente y deploy seguro de bajo costo.

## Tarea actual

Tambien se investiga `/debug` en produccion y se eleva la cobertura obligatoria a 100% de sentencias y ramas. El log remoto del intento mostrado por el usuario confirma `No pude enviar update de debug: Timed out`: el update grande tomo la ruta de documento y agoto el timeout HTTP predeterminado de cinco segundos.

El mecanismo mensual de backups GCE ya tiene un runbook exhaustivo y enlazado desde README/deploy para Galerazobot y futuros bots. El job diario de gasto de Google Cloud quedo implementado y validado; su activacion real sigue bloqueada porque `bot-fleet-production` no tiene dataset ni tabla de exportacion.

## Estado actual

- Rama `main`, tracking `origin/main`.
- Python 3.14.6 exacto y lock completo.
- `Dockerfile` tiene targets `test` y `runtime`; produccion corre como UID/GID 10001, con healthcheck SQLite.
- `compose.production.yaml` no publica puertos, usa la red del host para salida IPv6 y persiste `/app/data` y `/app/backups` en `/srv/galerazo`.
- Build/publicacion local: `scripts/deploy/Build-DockerImage.ps1` y `Publish-DockerImage.ps1`.
- Host/deploy: `Initialize-GceHost.ps1`, `Deploy-Gce.ps1` y `Rollback-Gce.ps1`, todos por IAP.
- El deploy remoto crea backup consistente, usa tag inmutable, espera healthcheck y restaura la imagen anterior si falla.
- GitHub `Publish GCE image` es exclusivamente manual, usa WIF y no contiene deploy automatico.
- Railway permanece desactivado y no fue modificado.
- Docker Desktop 4.83.0 esta instalado por usuario; Docker Engine 29.6.2 responde en contexto `desktop-linux` como Linux/amd64 sobre WSL 2.7.10. `hello-world` se ejecuto correctamente.
- Google Cloud CLI 576.0.0 esta instalado y autenticado; `core/project` apunta a `bot-fleet-production`, que se verifico `ACTIVE` mediante una lectura. No versionar ni registrar la cuenta humana autenticada.
- Los instaladores agregaron Docker y Google Cloud CLI al PATH de usuario. La sesion de Codex abierta antes de instalarlos conserva un PATH viejo; terminales nuevas los encuentran normalmente y, en esta sesion, se validaron usando sus rutas instaladas.
- La consola confirmo `bot-fleet-production` con USD 300 de credito de prueba sin uso y vencimiento mostrado para el 19 de octubre de 2026; no se pulso `Actualizar` ni se convirtio manualmente la cuenta a modalidad paga.
- `Bot Fleet - Monthly Guardrail` esta activo en USD, con presupuesto mensual de USD 1, USD 0 consumidos, promociones excluidas, Free Tier incluido y alertas real 10/50/100% mas pronostico 100%. Cubre la cuenta de facturacion, que actualmente tiene un solo proyecto; no es un corte automatico.
- Estan habilitadas `compute.googleapis.com`, `artifactregistry.googleapis.com`, `iap.googleapis.com` e `iamcredentials.googleapis.com`.
- `bigquery.googleapis.com` tambien esta habilitada. `bq ls --project_id=bot-fleet-production` no devuelve datasets; por eso el reporte sigue desactivado en produccion.
- Artifact Registry contiene `us-central1-docker.pkg.dev/bot-fleet-production/bots/galerazobot:e63c0e8ee924`, digest `sha256:21581c63d742902a2f13e2a987284531cdaee5469d09d7e93195cf7d1523e840`. Es la primera imagen publicada y usa el commit como tag.
- `galerazo-vm` existe y esta habilitada. Tiene exactamente un binding `roles/artifactregistry.reader` sobre `bots`, cero roles directos a nivel proyecto y cero claves administradas por el usuario.
- La cuenta humana activa de `gcloud` tiene exactamente un binding `roles/artifactregistry.writer` sobre `bots`; su identidad no se registra en la memoria ni en el repositorio.
- `scripts/deploy/Initialize-GcpBot.ps1` automatiza de forma idempotente APIs, registro e identidad/permisos por bot, encuentra `gcloud` instalado por usuario y no crea VM. Se ejecuto dos veces consecutivas con exito contra el proyecto real.
- La VPC custom `bot-fleet` contiene la subred `bots-us-central1` (`10.20.0.0/24`, `IPV4_IPV6`, IPv6 externo, Private Google Access) y exactamente una regla propia: tcp/22 desde IAP `35.235.240.0/20` al tag `iap-ssh`.
- `galerazo-prod` esta `RUNNING` en `us-central1-a`: `e2-micro`, Debian 12, disco de 30 GB `pd-standard`, sin IPv4 externa, con IPv6 efimera, `galerazo-vm`, OS Login, Shielded Secure Boot/vTPM/integrity monitoring y deletion protection. El contenedor de Galerazobot está `running/healthy`, sin OOM, con `restart_policy=unless-stopped`; Docker está activo y habilitado.
- El host remoto tiene Docker Engine 29.6.2, Compose 5.3.1 y Google Cloud CLI 576.0.0; Docker esta activo/habilitado. `/srv/galerazo/{data,backups}` pertenece a 10001:10001, `/etc/galerazo` esta protegido y `bot.env` real tiene modo 0600.
- `deploy/gce/verify-host.sh` valida el host sin imprimir secretos; `Initialize-GceHost.ps1` lo copia y ejecuta automaticamente. `--expect-pristine` confirmo cero contenedores, imagenes, base y Compose antes del primer deploy.
- `Set-GceBotSecrets.ps1` y la accion `Configure` transfieren solo las variables permitidas de `.env` mediante un temporal local, IAP y un directorio remoto 0700; `install-config.sh` instala como root 0600, conserva `bot.env.previous`, valida sin mostrar valores y limpia ambos temporales.
- La configuracion real ya se instalo en `galerazo-prod`: token e IDs presentes; OpenAI y Google Sheets omitidos porque estaban vacios localmente. `--expect-configured` paso, no quedaron directorios temporales y todavia hay cero imagenes, contenedores, Compose y base remota.
- `Migrate-GceBotDatabase.ps1` y la accion `MigrateData` exigen confirmacion, rechazan el bot local o contenedores remotos activos, crean un backup mediante la API SQLite, validan integridad y transfieren por un directorio IAP 0700. `install-database.sh` respalda/restaura una base remota previa y nunca copia WAL/SHM.
- La base real esta en `/srv/galerazo/data/galerazo.sqlite3`, owner 10001:10001, modo 0600, 176128 bytes y `integrity_check=ok`; el backup local queda en `backups/`, ignorado por Git. No quedaron temporales y siguen existiendo cero imagenes/contenedores y ningun Compose remoto.
- Bot Control Center ya dispone de una vista separada de credenciales. `Get-GceBotSecretStatus.ps1` devuelve sólo booleanos y `Patch-GceBotSecrets.ps1` aplica parches parciales por IAP sin valores en argumentos/salida, preserva campos omitidos, soporta el JSON opcional de Sheets, valida y limpia temporales.
- No hay Cloud Router/NAT ni direcciones reservadas. Se valido SSH por IAP, ruta IPv6 y conexion real por IPv6 a Telegram y por Private Google Access a Artifact Registry.
- `scripts/deploy/New-GceBotInstance.ps1` crea/valida esa infraestructura de forma idempotente y exige `-AcknowledgeBillableResource`. `Invoke-GceBotLifecycle.ps1` orquesta Foundation/Infrastructure/Prepare/Configure/MigrateData/Publish/Deploy/Release/Rollback y mantiene confirmaciones antes de costos, secretos, datos y produccion.
- `docs/DEPLOY_GCE.md` documenta la reproduccion en otra cuenta: alta/facturacion/login/presupuesto manuales y acciones automatizadas `Prepare`, `Configure`, `MigrateData` y `Release` con confirmaciones.
- `USER_QUEUE.md` no tiene pedidos sin procesar.

## Validacion reciente

- `docs/BACKUPS_GCE.md` quedó convertido en un runbook reproducible y su contrato documental quedó cubierto por prueba. Incluye arquitectura, costos, seguridad y aislamiento real, alta multibot, estado para Bot Control Center, restauración, pausa/retiro, troubleshooting y verificaciones periódicas. Pasaron 5 pruebas específicas y 126 pruebas completas, runtime, `pip check`, compileall y `git diff --check`.
- Backups mensuales activos: bucket privado `bot-fleet-production-sqlite-backups` en `us-central1`, retención 400 días, PAP y acceso uniforme; `galerazo-vm` sólo puede crear objetos. Timer enabled/active, próxima ejecución 2026-08-01 con demora aleatoria. Primera copia 180224 bytes descargada nuevamente: SHA-256 e `integrity_check` OK; bot remoto continuó `running/healthy`. Suite completa: 122 pruebas, runtime, pip, compileall, PowerShell/Bash y diff-check OK.
- Billing: 13 pruebas especificas validan timezone argentino, `invoice.month`, SQL parametrizado, costo bruto/creditos/neto, limite de 100 MiB, errores, destino de logging, default desactivado y `JobQueue`. La suite completa del worktree actual paso con 122 pruebas nativas, 62,72% de sentencias y 37,60% de ramas sobre el alcance multiplataforma; el panel Tk queda en sus pruebas Windows. Docker Linux/amd64 paso 121 pruebas (una Tk omitida), runtime Python 3.14.6 y smoke real de JobQueue/BigQuery. La imagen runtime local mide aproximadamente 110 MB y el import completo uso cerca de 99 MiB RSS.
- La configuracion de Billing se propaga por `.env`, el panel desplazable, bootstrap GCE, carga/parche/inspector remoto y documentacion. `Initialize-GceBillingReport.ps1` prepara dataset y permisos minimos solo con `-AcknowledgeBillableResource`; no se ejecuto contra GCP.
- `/galerazas` renderiza el título en negrita mediante `MessageEntity`, agrega una línea vacía antes de las filas y conserva ambas cosas al paginar. Pasaron 96 pruebas, runtime, `pip check`, `compileall` y `git diff --check`.
- Contrato de Bot Control Center completado: `deploy/gce/botctl.py` y `Invoke-GceBotctl.ps1` exponen acciones fijas para estado, triggers, multimedia, moderación y detención segura. La lectura real por IAP confirmó VM `running`, contenedor `running/healthy`, un reinicio total, cero reinicios recientes, Telegram conectado y seis triggers (cuatro con multimedia y dos de texto). No se ejecutaron mutaciones de producción.

- Cierre del primer deploy: dos auditorías remotas por IAP confirmaron contenedor `running/healthy`, SQLite legible, cero OOM, reinicios estables en 1 y tráfico Telegram `getUpdates`/`sendMessage` HTTP 200. La VM conservaba 433 MB disponibles y 25 GB libres en disco.
- Validación local posterior: 96 pruebas OK, runtime Python 3.14.6 alineado, `pip check`, `compileall`, `git diff --check` y checkpoint de logs sin novedades.
- 96 pruebas nativas OK.
- `compileall` OK para app, panel, paquete, scripts y tests.
- `scripts/runtime_versions.py`: runtime alineado.
- `pip check`: sin dependencias rotas.
- Parser PowerShell: todos los scripts de deploy sin errores.
- `bash -n`: bootstrap, instaladores de configuracion/base, verificador, deploy y rollback sin errores.
- `git diff --check`: limpio.
- El paso 10 ejecutó 96 pruebas dentro del target Docker (una prueba Tk omitida por ser Linux), validó Python 3.14.6 y construyó producción Linux/amd64. La imagen local y Artifact Registry coinciden en el digest `sha256:21581c...e840`.
- Lectura real desde Galerazo y Bot Control Center confirmó sólo ocho booleanos. Un no-op real mantuvo ausente `GOOGLE_SHEETS_SPREADSHEET_ID`, pasó el verificador remoto y no inició ni desplegó el bot.
- Docker y `gcloud` están instalados y validados; `deploy/out/last-image.txt` apunta a la imagen publicada y permanece ignorado por Git.
- Después de publicar se confirmó por IAP que la VM sigue con cero imágenes, cero contenedores y sin `/opt/galerazo/compose.yaml`.
- Antes del paso 11, el chequeo canónico del panel devolvió `BOT_APAGADO`; no había procesos Python con `app.py`, `data/bot.pid` ni contenedores Docker locales de Galerazobot. Este estado debe volver a comprobarse justo antes de desplegar porque es temporal.
- El primer intento publicó `d8ae2ecc00f5`, pero el runtime falló con `FileNotFoundError: /app/.python-version`. Se detuvo el reinicio continuo sin OOM; SQLite conservó 176128 bytes/mode 0600 y `bot.env` siguió root/0600.
- `db278a097b62` está publicado con digest `sha256:115a350c...b7cf7`; ejecutó 96 pruebas Docker, smoke de versión y healthcheck remoto sobre la base real como UID 10001. No inició Telegram durante esas comprobaciones.
- La inspección posterior encontró `db278a097b62` con 3081 reinicios y `telegram.error.TimedOut` durante `getMe`. La VM resolvió/alcanzó Telegram por IPv6; el bridge `galerazo_default` era `ipv6=false` y sólo resolvía `149.154.166.110`. La misma imagen con `--network host` resolvió también `2001:67c:4e8:f004::9` y obtuvo HTTP 200.
- El Compose con `network_mode: host` fue desplegado. Dos auditorías por IAP confirmaron `running/healthy`, healthcheck SQLite correcto, polling `getUpdates` HTTP 200 y envíos `sendMessage` HTTP 200. `/lil` respondió; hubo un reinicio inicial y luego no se registraron reinicios nuevos ni OOM.
- Quality `29779348254` y Docker Quality `29779348273` pasaron sobre `9ac8cc4`; Docker construyo el target de pruebas, ejecuto 89 tests y construyo el target runtime.

## Proximo paso exacto

Cuando el usuario confirme el posible costo, ejecutar `Initialize-GceBillingReport.ps1 -ProjectId bot-fleet-production -AcknowledgeBillableResource`, habilitar `Costo de uso estandar` sobre `billing_export` en la consola, esperar la tabla, configurar las tres variables de Billing y publicar/desplegar una imagen inmutable.

## Riesgos y bloqueos

- La VM `e2-micro` tiene 1 GB: limitar la moderacion de video concurrente hasta medir PyAV.
- La salida IPv6/Private Google Access fue validada; si una dependencia futura exige IPv4, Cloud NAT o IPv4 externa pueden agregar costo y requieren una nueva decision.
- Google Sheets real sigue bloqueado hasta recibir spreadsheet/worksheet/credenciales.
- El reporte diario de Billing no esta activo en produccion hasta crear/vincular el dataset y recibir la tabla generada por Google; la exportacion inicial puede tardar hasta cinco dias.
- No ejecutar el bot local y remoto simultaneamente con el mismo token.
