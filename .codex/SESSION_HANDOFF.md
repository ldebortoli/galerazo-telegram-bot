# Session handoff

## Objetivo general

Mantener Galerazo Bot reproducible en Windows, CI y Docker, con SQLite persistente y deploy seguro de bajo costo.

## Tarea actual

La preparacion de Google Cloud avanza paso a paso con el usuario. Los pasos 1 a 9 estan completos: infraestructura, host, secretos y SQLite remoto. Todavia no se publico ninguna imagen ni se hizo deploy del bot.

## Estado actual

- Rama `main`, tracking `origin/main`.
- Python 3.14.6 exacto y lock completo.
- `Dockerfile` tiene targets `test` y `runtime`; produccion corre como UID/GID 10001, con healthcheck SQLite.
- `compose.production.yaml` no publica puertos y persiste `/app/data` y `/app/backups` en `/srv/galerazo`.
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
- Artifact Registry contiene el repositorio Docker `bots` en `us-central1`, cifrado con clave administrada por Google. Al validarlo tenia 0 bytes y 0 imagenes.
- `galerazo-vm` existe y esta habilitada. Tiene exactamente un binding `roles/artifactregistry.reader` sobre `bots`, cero roles directos a nivel proyecto y cero claves administradas por el usuario.
- La cuenta humana activa de `gcloud` tiene exactamente un binding `roles/artifactregistry.writer` sobre `bots`; su identidad no se registra en la memoria ni en el repositorio.
- `scripts/deploy/Initialize-GcpBot.ps1` automatiza de forma idempotente APIs, registro e identidad/permisos por bot, encuentra `gcloud` instalado por usuario y no crea VM. Se ejecuto dos veces consecutivas con exito contra el proyecto real.
- La VPC custom `bot-fleet` contiene la subred `bots-us-central1` (`10.20.0.0/24`, `IPV4_IPV6`, IPv6 externo, Private Google Access) y exactamente una regla propia: tcp/22 desde IAP `35.235.240.0/20` al tag `iap-ssh`.
- `galerazo-prod` esta `RUNNING` en `us-central1-a`: `e2-micro`, Debian 12, disco de 30 GB `pd-standard`, sin IPv4 externa, con IPv6 efimera, `galerazo-vm`, OS Login, Shielded Secure Boot/vTPM/integrity monitoring y deletion protection.
- El host remoto tiene Docker Engine 29.6.2, Compose 5.3.1 y Google Cloud CLI 576.0.0; Docker esta activo/habilitado. `/srv/galerazo/{data,backups}` pertenece a 10001:10001, `/etc/galerazo` esta protegido y `bot.env` real tiene modo 0600.
- `deploy/gce/verify-host.sh` valida el host sin imprimir secretos; `Initialize-GceHost.ps1` lo copia y ejecuta automaticamente. `--expect-pristine` confirmo cero contenedores, imagenes, base y Compose antes del primer deploy.
- `Set-GceBotSecrets.ps1` y la accion `Configure` transfieren solo las variables permitidas de `.env` mediante un temporal local, IAP y un directorio remoto 0700; `install-config.sh` instala como root 0600, conserva `bot.env.previous`, valida sin mostrar valores y limpia ambos temporales.
- La configuracion real ya se instalo en `galerazo-prod`: token e IDs presentes; OpenAI y Google Sheets omitidos porque estaban vacios localmente. `--expect-configured` paso, no quedaron directorios temporales y todavia hay cero imagenes, contenedores, Compose y base remota.
- `Migrate-GceBotDatabase.ps1` y la accion `MigrateData` exigen confirmacion, rechazan el bot local o contenedores remotos activos, crean un backup mediante la API SQLite, validan integridad y transfieren por un directorio IAP 0700. `install-database.sh` respalda/restaura una base remota previa y nunca copia WAL/SHM.
- La base real esta en `/srv/galerazo/data/galerazo.sqlite3`, owner 10001:10001, modo 0600, 176128 bytes y `integrity_check=ok`; el backup local queda en `backups/`, ignorado por Git. No quedaron temporales y siguen existiendo cero imagenes/contenedores y ningun Compose remoto.
- Bot Control Center puede reutilizar la accion `Configure` para credenciales futuras. La UI especifica aun debe implementarse en su proyecto separado: campos enmascarados, mostrar solo presente/ausente, confirmacion, IAP y auditoria; nunca lectura de valores remotos.
- No hay Cloud Router/NAT ni direcciones reservadas. Se valido SSH por IAP, ruta IPv6 y conexion real por IPv6 a Telegram y por Private Google Access a Artifact Registry.
- `scripts/deploy/New-GceBotInstance.ps1` crea/valida esa infraestructura de forma idempotente y exige `-AcknowledgeBillableResource`. `Invoke-GceBotLifecycle.ps1` orquesta Foundation/Infrastructure/Prepare/Configure/MigrateData/Publish/Deploy/Release/Rollback y mantiene confirmaciones antes de costos, secretos, datos y produccion.
- `docs/DEPLOY_GCE.md` documenta la reproduccion en otra cuenta: alta/facturacion/login/presupuesto manuales y acciones automatizadas `Prepare`, `Configure`, `MigrateData` y `Release` con confirmaciones.
- `USER_QUEUE.md` no tiene pedidos sin procesar.

## Validacion reciente

- 95 pruebas nativas OK.
- `compileall` OK para app, panel, paquete, scripts y tests.
- `scripts/runtime_versions.py`: runtime alineado.
- `pip check`: sin dependencias rotas.
- Parser PowerShell: todos los scripts de deploy sin errores.
- `bash -n`: bootstrap, instaladores de configuracion/base, verificador, deploy y rollback sin errores.
- `git diff --check`: limpio.
- Docker y `gcloud` estan instalados y validados; no se publico ninguna imagen del bot.
- Las cuatro APIs requeridas y el repositorio Docker `bots` se validaron mediante `gcloud`; el registro estaba vacio y no habia VM.
- Quality `29779348254` y Docker Quality `29779348273` pasaron sobre `9ac8cc4`; Docker construyo el target de pruebas, ejecuto 89 tests y construyo el target runtime.

## Proximo paso exacto

Esperar que el usuario diga `siguiente` y continuar unicamente con el paso 10: ejecutar las pruebas/build Docker locales y publicar la primera imagen `linux/amd64` con tag inmutable en `bots/galerazobot` mediante `-Action Publish`. No desplegar ni iniciar el contenedor todavia.

## Riesgos y bloqueos

- La VM `e2-micro` tiene 1 GB: limitar la moderacion de video concurrente hasta medir PyAV.
- La salida IPv6/Private Google Access fue validada; si una dependencia futura exige IPv4, Cloud NAT o IPv4 externa pueden agregar costo y requieren una nueva decision.
- Google Sheets real sigue bloqueado hasta recibir spreadsheet/worksheet/credenciales.
- No ejecutar el bot local y remoto simultaneamente con el mismo token.
