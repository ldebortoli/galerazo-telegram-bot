# Session handoff

## Objetivo general

Mantener Galerazo Bot reproducible en Windows, CI y Docker, con SQLite persistente y deploy seguro de bajo costo.

## Tarea actual

La preparacion local para Google Compute Engine esta completa. No se crearon recursos GCP, credenciales, imagenes remotas ni deploys reales.

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
- `USER_QUEUE.md` no tiene pedidos sin procesar.

## Validacion reciente

- 89 pruebas nativas OK.
- `compileall` OK para app, panel, paquete, scripts y tests.
- `scripts/runtime_versions.py`: runtime alineado.
- `pip check`: sin dependencias rotas.
- Parser PowerShell: cuatro scripts de deploy sin errores.
- `bash -n`: bootstrap, deploy y rollback sin errores.
- `git diff --check`: limpio.
- Docker y gcloud no estan instalados en esta PC; no se construyo ni publico una imagen local y no se toco GCP. Docker Quality debe validar ambos targets despues del push.

## Proximo paso exacto

Seguir `docs/DEPLOY_GCE.md`: instalar Docker Desktop y Google Cloud CLI, crear proyecto/Artifact Registry/VM con service account, ejecutar `Initialize-GceHost.ps1`, completar `/etc/galerazo/bot.env`, publicar una imagen desde la PC y hacer el primer deploy con `Deploy-Gce.ps1`. Antes de migrar el token/base, apagar el bot local.

## Riesgos y bloqueos

- La VM `e2-micro` tiene 1 GB: limitar la moderacion de video concurrente hasta medir PyAV.
- IPv6 externo debe tener salida real hacia repositorios, Telegram y Artifact Registry; si algo requiere IPv4, Cloud NAT o IPv4 externa pueden agregar costo.
- Google Sheets real sigue bloqueado hasta recibir spreadsheet/worksheet/credenciales.
- No ejecutar el bot local y remoto simultaneamente con el mismo token.
