# Session handoff

## Objetivo general

Mantener Galerazo Bot reproducible en Windows, CI y Docker, con SQLite persistente y deploy seguro de bajo costo.

## Tarea actual

La preparacion de Google Cloud avanza paso a paso con el usuario. Los pasos 1 a 4 estan completos: proyecto/facturacion, presupuesto/alertas, herramientas locales y APIs/Artifact Registry. No se crearon todavia VM, service accounts, imagenes remotas ni deploys reales.

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
- Compute Engine tenia 0 VM al finalizar el paso 4.
- `USER_QUEUE.md` no tiene pedidos sin procesar.

## Validacion reciente

- 89 pruebas nativas OK.
- `compileall` OK para app, panel, paquete, scripts y tests.
- `scripts/runtime_versions.py`: runtime alineado.
- `pip check`: sin dependencias rotas.
- Parser PowerShell: cuatro scripts de deploy sin errores.
- `bash -n`: bootstrap, deploy y rollback sin errores.
- `git diff --check`: limpio.
- Docker y `gcloud` estan instalados y validados; no se publico ninguna imagen del bot.
- Las cuatro APIs requeridas y el repositorio Docker `bots` se validaron mediante `gcloud`; el registro estaba vacio y no habia VM.
- Quality `29779348254` y Docker Quality `29779348273` pasaron sobre `9ac8cc4`; Docker construyo el target de pruebas, ejecuto 89 tests y construyo el target runtime.

## Proximo paso exacto

Esperar que el usuario diga `siguiente` y continuar unicamente con el paso 5: crear la service account `galerazo-vm`, otorgarle lectura minima de Artifact Registry y verificar el permiso de publicacion local sin crear claves JSON. No crear todavia la VM. Antes de migrar el token/base en una etapa posterior, apagar el bot local.

## Riesgos y bloqueos

- La VM `e2-micro` tiene 1 GB: limitar la moderacion de video concurrente hasta medir PyAV.
- IPv6 externo debe tener salida real hacia repositorios, Telegram y Artifact Registry; si algo requiere IPv4, Cloud NAT o IPv4 externa pueden agregar costo.
- Google Sheets real sigue bloqueado hasta recibir spreadsheet/worksheet/credenciales.
- No ejecutar el bot local y remoto simultaneamente con el mismo token.
