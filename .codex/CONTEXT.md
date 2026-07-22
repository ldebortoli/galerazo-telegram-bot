# Galerazo Bot - Contexto del proyecto

## Descripcion general

Galerazo Bot es un bot de Telegram para chats privados, grupos, supergrupos y canales. Incluye administracion por niveles, listas paginadas, configuracion por chat, un juego diario llamado La Galeraza, triggers, registro de gastos con sincronizacion opcional a Google Sheets y un panel de control local para Windows.

La fuente de verdad operativa para agentes es esta carpeta `.codex/`. Al iniciar una sesion se deben leer, en orden: `CONTEXT.md`, `DECISIONS.md`, `BACKLOG.md`, `USER_QUEUE.md` y `SESSION_HANDOFF.md`.

La misma politica se aplica globalmente desde `C:\Users\calei\.codex\AGENTS.md`. Los proyectos nuevos se inicializan con `C:\Users\calei\.codex\project-memory\Initialize-ProjectMemory.ps1` antes de implementar su primera tarea.

## Stack tecnologico

- Python 3.14.6 exacto en Windows, CI y Docker; `.python-version` es la fuente canonica.
- `python-telegram-bot==22.8` para Telegram Bot API y polling.
- `python-telegram-bot[job-queue]` con APScheduler para tareas diarias.
- SQLite mediante `sqlite3` de la libreria estandar.
- `gspread` y `google-auth` para Google Sheets.
- `google-cloud-bigquery==3.42.2` y ADC para leer la exportacion estandar de Cloud Billing.
- `python-dotenv` para configuracion local desde `.env`.
- `httpx` para consultar OpenAI Moderation, `Pillow` para normalizar imagenes y `PyAV` para extraer frames de video completamente en memoria.
- `tzdata==2026.3` para convertir timestamps de Telegram al timezone IANA argentino tambien en Windows.
- `coverage.py==7.15.2` para cobertura local/CI de sentencias y ramas.
- Tkinter para el panel de escritorio de Windows.
- Un lanzador minimo en C#/.NET Framework para abrir el panel sin consola.
- Docker para deploy.
- GitHub Actions preparado para Railway, actualmente desactivado.

## Arquitectura

- `app.py`: entrypoint del bot Telegram.
- `AGENTS.md`: punto de entrada que obliga a cargar la memoria persistente.
- `control_panel.py`: entrypoint del panel local de Windows.
- `galerazo_bot/telegram_bot.py`: integracion con `python-telegram-bot`, registro de handlers y adaptacion de updates/callbacks al dominio.
- `galerazo_bot/commands.py`: dispatcher comun, normalizacion, permisos y ejecucion de comandos.
- `galerazo_bot/command_handlers/`: un modulo por conjunto de comandos. Cada modulo exporta `COMMANDS`.
- `galerazo_bot/database.py`: esquema SQLite y operaciones persistentes.
- `galerazo_bot/pagination.py`: paginacion reutilizable y metadata de botoneras.
- `galerazo_bot/chat_config.py`: menus y grupos de comandos configurables.
- `galerazo_bot/i18n.py`: textos en espanol e ingles. Los nombres de comandos no se traducen.
- `galerazo_bot/galeraza.py`: reglas y formato del juego diario.
- `galerazo_bot/media_moderation.py`: normalizacion de imagenes, muestreo 20/40/60/80% de videos y cliente de moderacion; no persiste media.
- `galerazo_bot/command_handlers/ruletarusa.py`: juego persistente de seis recamaras y seleccion de objetivo por nivel.
- `galerazo_bot/expenses.py` y `google_sheets.py`: gastos, formato y sincronizacion.
- `galerazo_bot/cloud_billing.py`: consulta mensual de Billing, limite de bytes y formato del reporte diario.
- `galerazo_bot/control_panel.py`: UI local, manejo del proceso, `.env` y logs.
- `launcher/GalerazoBotControlLauncher.cs`: lanzador Windows.
- `assets/`: PNG fuente e ICO multirresolucion del conejo con galera; todas las capas ICO son DIB BGRA de 32 bits con alfa y mascara AND. Las capas de 16 a 64 px usan una composicion compacta del conejo/cara/ala de la galera; 128 y 256 px conservan el arte completo.
- `tests/`: pruebas `unittest` de regresion y comportamiento.
- `.github/workflows/deploy.yml`: deploy Railway desactivado y disponible solo por ejecucion manual.
- `.github/workflows/quality.yml`: suite Linux para cambios sustantivos; ignora documentacion/memoria y cancela runs obsoletos.
- `.github/workflows/docker-quality.yml`: build y tests Docker solo cuando cambia el runtime o la configuracion del contenedor.
- `.github/workflows/publish-gce-image.yml`: publicacion manual del target Docker de produccion en Artifact Registry mediante Workload Identity Federation; nunca corre por push.
- `.github/workflows/runtime-update.yml`: actualizacion semanal de Python/dependencias; salta validaciones cuando no hay cambios y, despues de validar entorno nativo y Docker, publica un commit normal sobre `main` sin force push ni permisos de pull request.
- `requirements.in`: dependencias directas; `requirements.txt`: lock completo reproducible.
- `scripts/runtime_versions.py`: valida y sincroniza la version exacta entre runtime y Docker.
- `scripts/check_coverage.py`: exige 62% de sentencias y 36% de ramas sobre `galerazo_bot`.
- `scripts/deploy/Initialize-GceBillingReport.ps1`: prepara BigQuery y permisos minimos con confirmacion de posible costo; la vinculacion de Billing se hace en consola.
- `compose.production.yaml`: servicio de produccion sin puertos, no root, filesystem de solo lectura, volumenes persistentes para SQLite/backups y red de host para reutilizar la salida IPv6 de la VM sin IPv4 publica/NAT.
- `scripts/deploy/`: ciclo GCP reproducible por etapas, build/publicacion local, bootstrap, configuracion secreta, migracion SQLite, deploy por IAP y rollback. El build prueba también el target runtime real con `ensure_python_version()` antes de publicarlo. Incluye inspeccion booleana y parches parciales de credenciales para Bot Control Center, y `Invoke-GceBotctl.ps1` para estado, triggers, multimedia, moderacion y detencion segura, siempre mediante scripts fijos y temporales privados. `Invoke-GceBotLifecycle.ps1` orquesta Foundation/Infrastructure/Prepare/Configure/MigrateData/Publish/Deploy/Release/Rollback con confirmaciones.
- `deploy/gce/`: scripts remotos idempotentes para instalar Docker/Cloud CLI, instalar o parchear configuracion/base privadas con rollback, verificar servicio/permisos sin imprimir secretos, desplegar con healthcheck y restaurar la imagen anterior. `botctl.py` implementa el contrato efimero de Bot Control Center sin instalar un servicio ni abrir puertos.
- `docs/DEPLOY_GCE.md`: setup completo de Free Tier, IPv6/IAP, Artifact Registry, secretos, migracion y operacion.
- `docs/BACKUPS_GCE.md`: runbook reproducible de backups mensuales para la flota; documenta arquitectura, costos, seguridad, operación, restauración, diagnóstico, contrato de estado para Bot Control Center y alta de otros bots.
- `scripts/sync_windows_runtime.ps1`: instala/verifica el Python exacto con winget, conserva una `.venv` valida o la recrea cuando corresponde, e instala/valida el lock.
- `scripts/setup.ps1`: setup integral e idempotente de Windows; compone runtime, configuracion local, validacion, build, accesos directos y apertura del panel.
- `instaladores/Instalar Galerazo Bot.cmd`: puente de doble clic hacia el setup versionado; no copia el repo ni contiene secretos.

## Persistencia y consistencia

- La base por defecto es `data/galerazo.sqlite3`.
- Cada operacion abre una conexion corta mediante un context manager y garantiza commit/rollback y cierre explicito.
- Todos los datos asociados a un `chat_id` deben migrarse cuando Telegram convierte un grupo en supergrupo.
- `Database.migrate_chat_id` es el punto central de esa migracion.
- El bot usa `PerChatUpdateProcessor`: conserva orden FIFO dentro de cada chat y permite procesar chats distintos en paralelo.
- El polling fija `drop_pending_updates=False` para consumir updates que Telegram todavia conserve.
- Los callbacks de botoneras se procesan en la misma secuencia del chat correspondiente.
- La Galeraza usa una insercion atomica para garantizar un ganador por chat y dia.
- La fecha de La Galeraza sale exclusivamente de `message.date` de Telegram convertido a `America/Argentina/Buenos_Aires`; todo `message` original de grupo/supergrupo con autor humano compite, incluidos los eventos de servicio. Bots, ediciones y updates sin usuario no compiten.
- La ruleta rusa usa `BEGIN IMMEDIATE` para consumir atomicamente una recamara por usuario/chat; viene deshabilitada por defecto y migra con el chat.
- Los datos de chats no se eliminan cuando el bot es expulsado o bloqueado; solo cambia su estado de actividad.

## Configuracion

Copiar `.env.example` a `.env`. Variables:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_DEV_USER_IDS`
- `TELEGRAM_LOG_CHAT_ID`
- `TELEGRAM_ANNOUNCEMENTS_CHAT_ID`
- `DATABASE_PATH`
- `GOOGLE_SHEETS_CREDENTIALS_JSON_PATH`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_WORKSHEET_NAME`
- `OPENAI_API_KEY` opcional; debe ser una clave restringida a escritura en `/v1/moderations` y el panel la trata como secreto.
- `GOOGLE_CLOUD_BILLING_PROJECT_ID`
- `GOOGLE_CLOUD_BILLING_TABLE` en formato `project.dataset.table`
- `GOOGLE_CLOUD_BILLING_REPORT_TIME` en formato `HH:MM`, default `09:00` de Argentina.

`.env`, credenciales, bases, backups, logs y PID locales no se versionan.

## Comandos importantes de desarrollo

Instalar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Alternativa de doble clic: `instaladores\Instalar Galerazo Bot.cmd`.

Ejecutar bot:

```powershell
python app.py
```

Ejecutar panel:

```powershell
pythonw control_panel.py
```

Reconstruir lanzador Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_control_panel.ps1
```

El build crea `Galerazo Bot.lnk` tanto en el directorio hermano `CODEX APPS` como en el Escritorio del usuario.

Validaciones disponibles:

```powershell
python -m compileall app.py control_panel.py galerazo_bot
python -m galerazo_bot.cli hola
python -m galerazo_bot.cli help
python -m galerazo_bot.cli nivel
python -m unittest discover -s tests -v
python -m coverage run -m unittest discover -s tests -v
python -m coverage json
python scripts/check_coverage.py
python scripts/runtime_versions.py
python -m galerazo_bot.log_checkpoint
git diff --check
```

La suite automatizada usa `unittest` y cubre enrutamiento, permisos, config, Galeraza, ruleta, triggers, migraciones con colisiones, paginacion, serializacion de debug, logging, panel e instancia unica. La cobertura obligatoria del nucleo multiplataforma es 100% de sentencias y ramas; `galerazo_bot/control_panel.py` queda explicitamente fuera de esa metrica por depender del layout Tk nativo de Windows, donde mantiene su prueba especifica. La cobertura de Galeraza audita las 46 categorias actuales de `filters.StatusUpdate` y falla si PTB agrega una nueva sin mapear.

El panel usa un cliente inicial de `760x750`, minimo `680x730`; la pestaña Configuracion desplaza solamente el formulario y mantiene visibles las acciones y el estado del canal de logging.

## Convenciones de codigo

- ASCII por defecto en archivos nuevos.
- Handlers y auxiliares especificos de un comando viven juntos en `command_handlers/<grupo>.py`.
- Registrar cada modulo nuevo en `command_handlers/__init__.py`.
- Reutilizar APIs de `python-telegram-bot` antes de implementar equivalentes propios.
- Usar siempre `.venv`; no ejecutar el proyecto con el alias global `python` sin activar el entorno.
- Mantener la ultima version estable de CPython y dependencias; todo upgrade debe actualizar el lock y pasar tests nativos y Docker o revertirse.
- Las listas de usuarios muestran siempre el user ID entre parentesis.
- Las listas largas usan la paginacion reutilizable y nunca cortan un renglon.
- Los comandos conservan sus nombres originales en todos los idiomas.
- Los comandos aceptan `/`, `!`, `.`, `>`, `$`, `galerazobot` y `galerazo_bot` como prefijos.
- Los comandos inexistentes se ignoran silenciosamente; no registrar fallbacks en grupos posteriores de PTB que vuelvan a procesar comandos validos.
- Antes de cerrar cada pedido se ejecuta `python -m galerazo_bot.log_checkpoint`; los errores nuevos se investigan antes de reconocer y avanzar el offset.
- Los rankings usan nombres visibles cacheados en `users` y user IDs; no generan menciones ni hacen requests de nombres al renderizar.
- Todas las pantallas de `/config` incluyen `config:close`; los permisos se validan antes de ejecutar cualquier callback.
- Cerrar el panel de control apaga el arbol de procesos local del bot antes de destruir la ventana.
- Los niveles se validan al invocar comandos o tocar botones, no como clasificacion global permanente.
- La media se modera solo al crear triggers. Sin clave se omite; con clave, un fallo impide guardar ese intento. Los buffers y frames se mantienen en memoria y se limpian siempre.

## Git y deploy

- Repositorio remoto: `https://github.com/ldebortoli/galerazo-telegram-bot.git`.
- Rama principal: `main`, con tracking de `origin/main`.
- El flujo historico del proyecto usa commits directos a `main`; usar ramas `codex/<nombre>` si un trabajo futuro requiere PR o aislamiento.
- Antes de cerrar una sesion, actualizar `.codex/`, validar, committear y pushear si el remoto sigue configurado.
- No activar `.github/workflows/deploy.yml` hasta que el usuario lo pida explicitamente y existan los secrets de Railway.
- El camino recomendado de produccion es GCE + Docker Compose + Artifact Registry. Construir/publicar localmente es el default para no consumir Actions; GitHub solo publica imagenes por `workflow_dispatch`.
- El proyecto GCP personal para la flota es `bot-fleet-production`; cada bot conserva VM/contenedor, service account, datos y secretos con nombres especificos. Un proyecto separado se reserva para clientes, facturacion o permisos que requieran aislamiento fuerte.
- En `bot-fleet-production` estan habilitadas las APIs de Compute Engine, Artifact Registry, IAP, IAM Service Account Credentials y Cloud Storage. El registro Docker compartido para la flota es `bots` en `us-central1`; cada bot usa su propio nombre de imagen.
- BigQuery API esta habilitada, pero todavia no existe ningun dataset ni exportacion de Billing. No crear el dataset sin `-AcknowledgeBillableResource`; despues se debe habilitar manualmente el costo de uso estandar y esperar la tabla.
- La imagen corregida más reciente de Galerazo es `galerazobot:db278a097b62`, Linux/amd64, digest `sha256:115a350c8bc9c90a352abf6176b13f669375a2472a4c2172f79b589ed34b7cf7`. Reemplaza para deploy a `e63c0e8ee924` y `d8ae2ecc00f5`; esta última falló porque el runtime omitía `.python-version`. `deploy/out/last-image.txt` conserva localmente la referencia más reciente y está ignorado por Git.
- `galerazo-vm` es la identidad de runtime de Galerazobot: esta habilitada, tiene `roles/artifactregistry.reader` sobre `bots` y `roles/storage.objectCreator` sobre el bucket privado de backups, ningún rol directo a nivel proyecto y cero claves administradas por el usuario. La cuenta local activa tiene `roles/artifactregistry.writer` solo sobre `bots`.
- La infraestructura de Galerazobot usa VPC custom `bot-fleet`, subred `bots-us-central1` dual-stack externa `10.20.0.0/24`, Private Google Access y una unica regla de esa VPC: SSH tcp/22 desde IAP hacia el tag `iap-ssh`. `galerazo-prod` es `e2-micro` en `us-central1-a`, Debian 12, 30 GB `pd-standard`, sin IPv4 externa, con IPv6 efimera, OS Login, Shielded VM y deletion protection.
- El host `galerazo-prod` ejecuta `galerazobot:db278a097b62` mediante Compose con `network_mode: host` para reutilizar la salida IPv6 de la VM. El contenedor está `running/healthy`, Telegram mantiene polling y envíos HTTP 200, la política de reinicio es `unless-stopped` y Docker está activo/habilitado. `bot.env` permanece root/0600 sin OpenAI/Google Sheets y SQLite está instalado como 10001:10001/0600, legible e íntegro.
- Los backups SQLite mensuales de la flota usan `bot-fleet-production-sqlite-backups` en `us-central1`, acceso uniforme, prevención de acceso público, soft delete de siete días y ciclo de vida de 400 días bajo `bots/<bot-id>/`. Cada VM ejecuta una copia consistente con SHA-256 mediante un timer systemd persistente y sólo puede crear objetos. Galerazobot tiene una primera copia remota verificada y estado local en `/srv/galerazo/backups/monthly`.
- En el bucket compartido, `bots/<bot-id>/` es aislamiento lógico y no una frontera IAM: las VMs personales comparten confianza y `storage.objectCreator` a nivel bucket. Bots de clientes o dominios no confiables deben usar bucket o proyecto separado.
