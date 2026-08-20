# Galerazo Bot - Contexto del proyecto

## Descripcion general

Galerazo Bot es un bot de Telegram para chats privados, grupos, supergrupos y canales. Incluye administracion por niveles, listas paginadas, configuracion por chat, La Galeraza, el Recolector de Hisopos, triggers, registro de gastos con sincronizacion opcional a Google Sheets y un panel de control local para Windows.

La fuente de verdad operativa para agentes es esta carpeta `.codex/`. Al iniciar una sesion se deben leer, en orden: `CONTEXT.md`, `DECISIONS.md`, `BACKLOG.md`, `USER_QUEUE.md` y `SESSION_HANDOFF.md`.

La misma politica se aplica globalmente desde `C:\Users\calei\.codex\AGENTS.md`. Los proyectos nuevos se inicializan con `C:\Users\calei\.codex\project-memory\Initialize-ProjectMemory.ps1` antes de implementar su primera tarea.

## Stack tecnologico

- Python 3.14.6 exacto en Windows, CI y Docker; `.python-version` es la fuente canonica.
- `python-telegram-bot==22.8` para Telegram Bot API y polling.
- `python-telegram-bot[job-queue]` con APScheduler para tareas diarias.
- SQLite mediante `sqlite3` de la libreria estandar.
- `gspread` y `google-auth` para Google Sheets.
- `google-cloud-bigquery==3.43.0` y ADC para leer la exportacion estandar de Cloud Billing.
- `python-dotenv` para configuracion local desde `.env`.
- `httpx` para consultar OpenAI Moderation, `Pillow` para normalizar imagenes y `PyAV` para extraer frames de video completamente en memoria.
- `tzdata==2026.3` para convertir timestamps de Telegram al timezone IANA argentino tambien en Windows.
- `coverage.py==7.15.4` para cobertura local/CI de sentencias y ramas.
- `pytest==9.1.1` como runner de pruebas y `pytest-asyncio==1.4.0` con modo automatico para futuros tests async nativos.
- Tkinter para el panel de escritorio de Windows.
- Un lanzador minimo en C#/.NET Framework para abrir el panel sin consola.
- Docker para deploy.
- GitHub Actions preparado para Railway, actualmente desactivado.

## Arquitectura

- `app.py`: entrypoint del bot Telegram.
- `AGENTS.md`: punto de entrada que obliga a cargar la memoria persistente.
- `control_panel.py`: entrypoint del panel local de Windows.
- `galerazo_bot/telegram_bot.py`: ciclo de vida e integracion con `python-telegram-bot`; conserva adaptadores comunes y delega el registro nativo de handlers.
- `galerazo_bot/telegram_retry.py`: `RetryingExtBot` comun para todos los envios de texto; reintenta exclusivamente `TimedOut` hasta tres intentos totales y conserva la configuracion HTTP de PTB.
- `galerazo_bot/handler_registration.py`: registro central de `MessageHandler`, `CommandHandler`, `PrefixHandler`, `CallbackQueryHandler` y `ChatMemberHandler`, sin fallback que interprete texto libre como comando.
- `galerazo_bot/command_model.py`: contrato ligero `Command`, separado del dispatcher para que los modulos de dominio no dependan de `commands.py`.
- `galerazo_bot/commands.py`: dispatcher comun, normalizacion, permisos y ejecucion de comandos.
- `galerazo_bot/command_handlers/`: un modulo por conjunto de comandos. Cada modulo exporta `COMMANDS` y, cuando posee datos por chat, su migrador `migrate_chat_data`; `galerazas.py` tambien contiene los adaptadores de Telegram que otorgan y envian el ranking.
- `galerazo_bot/chat_migration.py`: normaliza ambos eventos de migracion de Telegram y coordina los migradores de dominio dentro de una unica transaccion SQLite.
- `galerazo_bot/database.py`: esquema SQLite, operaciones persistentes y la parte comun de cada migracion de chat.
- `galerazo_bot/pagination.py`: paginacion reutilizable y metadata de botoneras.
- `galerazo_bot/chat_config.py`: menus y grupos de comandos configurables.
- `galerazo_bot/versioning.py`: version actual y lectura de la entrada correspondiente en `CHANGELOG.md`.
- `galerazo_bot/i18n.py` y `galerazo_bot/extra_translations.py`: textos en espanol argentino (default), espanol de Espana, ingles, ruso, latin, japones, italiano, frances, aleman, holandes, chino simplificado/tradicional, portugues de Brasil/Portugal, catalan, vasco, guarani y Quechua sureño (`quz`, Runa Simi). Los nombres de comandos no se traducen.
- `galerazo_bot/galeraza.py`: reglas y formato del juego diario.
- `galerazo_bot/media_moderation.py`: normalizacion de imagenes, muestreo 20/40/60/80% de videos y cliente de moderacion; no persiste media.
- `galerazo_bot/command_handlers/ruletarusa.py`: juego persistente de seis recamaras y seleccion de objetivo por nivel.
- `galerazo_bot/expenses.py` y `google_sheets.py`: gastos, formato y sincronizacion.
- `galerazo_bot/cloud_billing.py`: consulta mensual de Billing, limite de bytes y formato del reporte diario.
- `galerazo_bot/control_panel.py`: UI local, manejo del proceso, `.env` y logs.
- `launcher/GalerazoBotControlLauncher.cs`: lanzador Windows.
- `assets/`: PNG fuente e ICO multirresolucion del conejo con galera; todas las capas ICO son DIB BGRA de 32 bits con alfa y mascara AND. Las capas de 16 a 64 px usan una composicion compacta del conejo/cara/ala de la galera; 128 y 256 px conservan el arte completo.
- `tests/`: pruebas de regresion y comportamiento; el runner oficial es `pytest`, compatible con los casos heredados `unittest` e `IsolatedAsyncioTestCase`.
- `.github/workflows/deploy.yml`: deploy Railway desactivado y disponible solo por ejecucion manual.
- `.github/workflows/quality.yml`: suite Linux para cambios sustantivos; ignora documentacion/memoria y cancela runs obsoletos.
- `.github/workflows/docker-quality.yml`: build y tests Docker solo cuando cambia el runtime o la configuracion del contenedor.
- `.github/workflows/publish-gce-image.yml`: publicacion manual del target Docker de produccion en Artifact Registry mediante Workload Identity Federation; nunca corre por push.
- `.github/workflows/runtime-update.yml`: actualizacion semanal de Python/dependencias; salta validaciones cuando no hay cambios, ejecuta la suite nativa una sola vez y valida el target Docker `runtime` con su comprobacion de version antes de publicar un commit normal sobre `main`, sin force push ni permisos de pull request.
- `requirements.in`: dependencias directas; `requirements.txt`: lock completo reproducible.
- `scripts/runtime_versions.py`: valida y sincroniza la version exacta entre runtime y Docker.
- `scripts/check_coverage.py`: exige 100% de sentencias y 100% de ramas sobre el nucleo multiplataforma de `galerazo_bot`.
- `scripts/deploy/Initialize-GceBillingReport.ps1`: prepara BigQuery y permisos minimos con confirmacion de posible costo; la vinculacion de Billing se hace en consola.
- `compose.production.yaml`: servicio de produccion sin puertos, no root, filesystem de solo lectura, volumenes persistentes para SQLite/backups y red de host para reutilizar la salida IPv6 de la VM sin IPv4 publica/NAT.
- `scripts/deploy/`: ciclo GCP reproducible por etapas, build/publicacion local, bootstrap, configuracion secreta, migracion SQLite, deploy por IAP y rollback. El build prueba también el target runtime real con `ensure_python_version()` antes de publicarlo. Incluye inspeccion booleana y parches parciales de credenciales para Bot Control Center, y `Invoke-GceBotctl.ps1` para estado, triggers, multimedia, moderacion y detencion segura, siempre mediante scripts fijos y temporales privados. `Invoke-GceBotLifecycle.ps1` orquesta Foundation/Infrastructure/Prepare/Configure/MigrateData/Publish/Deploy/Release/Rollback con confirmaciones.
- `deploy/gce/`: scripts remotos idempotentes para instalar Docker/Cloud CLI, instalar o parchear configuracion/base privadas con rollback, verificar servicio/permisos sin imprimir secretos, desplegar con healthcheck y restaurar la imagen anterior. `botctl.py` implementa el contrato efimero de Bot Control Center sin instalar un servicio ni abrir puertos.
- `docs/DEPLOY_GCE.md`: setup completo de Free Tier, IPv6/IAP, Artifact Registry, secretos, migracion y operacion.
- `docs/BACKUPS_GCE.md`: runbook reproducible de backups mensuales para la flota; documenta arquitectura, costos, seguridad, operación, restauración, diagnóstico, contrato de estado para Bot Control Center y alta de otros bots.
- `scripts/sync_windows_runtime.ps1`: instala/verifica el Python exacto con winget, conserva una `.venv` valida o la recrea cuando corresponde, e instala/valida el lock.
- `scripts/setup.ps1`: setup integral e idempotente de Windows; compone runtime, configuracion local, validacion, build, accesos directos y apertura del panel.
- `scripts/Watch-GceBotLogs.ps1`: abre por IAP una lectura continua y de solo lectura de los logs Docker de produccion. `build_control_panel.ps1` crea `Galerazo Bot - Logs.lnk` en `CODEX APPS` para ejecutarlo en PowerShell.
- `instaladores/Instalar Galerazo Bot.cmd`: puente de doble clic hacia el setup versionado; no copia el repo ni contiene secretos.

## Persistencia y consistencia

- La base por defecto es `data/galerazo.sqlite3`.
- Cada operacion abre una conexion corta mediante un context manager y garantiza commit/rollback y cierre explicito.
- Todos los datos asociados a un `chat_id` deben migrarse cuando Telegram convierte un grupo en supergrupo. Un `MessageHandler(filters.StatusUpdate.MIGRATE)` dedicado recibe los eventos antes del preprocesador general.
- Telegram entrega dos eventos de migracion. `Database.migrate_chat_id` reclama de forma atomica el par `old_chat_id`/`new_chat_id` en `chat_migrations`; solo el primer evento mueve datos y el segundo no realiza cambios.
- `Database.migrate_chat_id` conserva una sola transaccion: actualiza las tablas comunes y llama a `chat_migration.migrate_command_data`, que delega cada tabla de comando a su modulo propietario.
- El bot usa `PerChatUpdateProcessor`: conserva orden FIFO dentro de cada chat y permite procesar chats distintos en paralelo.
- El polling fija `drop_pending_updates=False` para consumir updates que Telegram todavia conserve.
- Los callbacks de botoneras se procesan en la misma secuencia del chat correspondiente.
- La Galeraza usa una insercion atomica para garantizar un ganador por chat y dia.
- La fecha de La Galeraza sale exclusivamente de `message.date` de Telegram convertido a `America/Argentina/Buenos_Aires`; todo `message` original de grupo/supergrupo con autor humano compite, incluidos los eventos de servicio. Bots, ediciones y updates sin usuario no compiten.
- El Recolector de Hisopos viene deshabilitado por defecto. Por cada mensaje valido tira contra 1/5/10/15/20% segun intensidad; sus tres rarezas valen 1/2/3 puntos. Las capturas son atomicas, vencen a los 20 minutos y cada premio agenda en SQLite una aparicion aleatoria para el siguiente dia argentino.
- Una captura exitosa edita la leyenda de la foto original, elimina la botonera y muestra el nombre visible del ganador, el tipo de Hisopo y los puntos obtenidos. Al pudrirse tambien elimina la botonera. Si se incorporan rarezas con puntaje negativo, el resultado debe distinguir en cada idioma entre puntos ganados y perdidos.
- Las fotos del Recolector se reenvian con `TELEGRAM_HISOPO_COMMON_FILE_ID`, `TELEGRAM_HISOPO_SILVER_FILE_ID` y `TELEGRAM_HISOPO_GOLD_FILE_ID`. Los artes fuente versionados viven en `assets/hisopos/`.
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
python -m galerazo_bot.cli /hola
python -m galerazo_bot.cli help
python -m galerazo_bot.cli nivel
python -m pytest
python -m coverage run -m pytest
python -m coverage json
python scripts/check_coverage.py
python scripts/runtime_versions.py
python -m galerazo_bot.log_checkpoint
git diff --check
```

La suite automatizada usa `pytest` y cubre enrutamiento, permisos, config, Galeraza, ruleta, triggers, migraciones con colisiones, paginacion, serializacion de debug, logging, panel e instancia unica. Conserva los casos heredados `unittest` e `IsolatedAsyncioTestCase`, y `pytest-asyncio` permite agregar tests async nativos. La cobertura obligatoria del nucleo multiplataforma es 100% de sentencias y ramas; `galerazo_bot/control_panel.py` queda explicitamente fuera de esa metrica por depender del layout Tk nativo de Windows, donde mantiene su prueba especifica. La cobertura de Galeraza audita las 46 categorias actuales de `filters.StatusUpdate` y falla si PTB agrega una nueva sin mapear.

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
- Los comandos aceptan `/`, `!`, `.`, `>` y `$` como prefijos. Los comandos con `/` tambien admiten el sufijo nativo `@nombre_del_bot` que reconoce `CommandHandler`.
- Los comandos inexistentes se ignoran silenciosamente; no registrar fallbacks en grupos posteriores de PTB que vuelvan a procesar comandos validos.
- Antes de cerrar cada pedido se ejecuta `python -m galerazo_bot.log_checkpoint`; los errores nuevos se investigan antes de reconocer y avanzar el offset.
- Los `NetworkError` transitorios de `getUpdates` llegan sin update/job/coroutine y PTB los reintenta; se registran como warning local sin anunciar un falso error no handleado. Errores de red asociados a trabajo real si se anuncian.
- El bot usa `RetryingExtBot` para todos los `send_message`, incluidos los `reply_text`: ante `TimedOut` realiza tres intentos totales (original y dos reintentos) con esperas de 1 y 2 segundos, deteniendose al primer exito. Se prioriza la entrega y se acepta que Telegram pueda haber aceptado intentos sin confirmarlos, por lo que pueden existir duplicados. El tercer timeout se eleva y registra como error. `ApplicationBuilder` conserva 30 segundos para los timeouts HTTP normales. En La Galeraza el punto ya persistido se conserva y el error final tambien llega al canal de logging con el conteo de intentos.
- Al iniciar, el bot sincroniza los comandos sugeridos de BotFather por scope: privados reciben los comandos generales; grupos reciben comandos comunes excepto gastos y sus administradores reciben ademas los comandos `ADMIN`. Los comandos `DEV` y todos los de gastos no se sugieren; el menu global se limpia para no filtrarlos a canales.
- `CURRENT_VERSION` es `0.17`; `CHANGELOG.md` contiene las notas por release y se actualiza con todo cambio funcional. El agente calcula la siguiente version salvo numero indicado por el usuario: capacidades importantes incrementan la menor y arreglos menores se agrupan como "Correcciones y mejoras". Si un comando cambia, tambien actualiza y sincroniza BotFather en esa ejecucion. SQLite anuncia cada version una vez al canal de novedades y `/version` la expone a todos.
- `CHANGELOG.md` y las novedades distribuidas son publicos: solo describen cambios visibles para usuarios en comandos publicos. No mencionar comandos DEV, infraestructura, Docker, SQLite, migraciones, despliegues ni correcciones internas; esas notas viven en commits, documentacion tecnica y `.codex/`.
- `/anuncio` es exclusivo de desarrollo. Envia el texto a los chats activos que tengan anuncios habilitados y al canal de anuncios, anexa el acceso a `/config` y valida el limite final antes de comenzar. Un error definitivo de Telegram marca el chat inactivo; timeouts y red transitoria no lo hacen. Los changelogs de una version desplegada usan el mismo envio.
- Al finalizar un broadcast automatico de release que alcanzo el canal de anuncios, el bot envia al canal de logging el mismo resumen de contadores que devuelve `/anuncio`. El fallo de ese resumen no altera la marca de version anunciada.
- La imagen runtime incluye `CHANGELOG.md`. Si las notas no pueden leerse durante el inicio, el bot registra el fallo localmente y lo reenvia al canal de logging sin impedir el arranque.
- Los anuncios dejan una linea en blanco antes del canal y luego muestran en lineas consecutivas el texto de donacion, `Repo: https://github.com/ldebortoli/galerazo-telegram-bot` y el aviso de `/config`, sin espacios adicionales.
- Todos los anuncios incluyen antes de la donacion el canal `https://t.me/+AqjGXXgEg-43YTMx`; la etiqueta se localiza como `Anuncios` o `Announcements`. La etiqueta `Repo` y su URL son invariantes entre idiomas.
- Los broadcasts, `/novedad` y changelogs distribuidos deshabilitan previews de enlaces mediante la API nativa de PTB.
- `CHANGELOG.md` conserva Markdown para el repositorio, pero las novedades distribuidas remueven los delimitadores de codigo en linea antes de enviarse como texto plano a Telegram.
- El resumen de `/anuncio` presenta cada contador en una línea separada.
- `/donar` es publico y devuelve el enlace de Cafecito. Los broadcasts incluyen el mismo texto antes del aviso de `/config`.
- `/reiniciarbot` y `/apagar` son exclusivos DEV: crean un tablero privado de cinco minutos. El solicitante puede confirmar o cancelar; clicks ajenos reciben popup. La expiracion se limpia bajo demanda; al confirmar, detienen polling, drenan las updates ya aceptadas y reinician o apagan el proceso. El drenaje tiene un limite de 60 segundos, registra el timeout en logging y fuerza la accion. Las updates posteriores se recuperan al inicio porque el polling no descarta pendientes.
- Los deploys Docker esperan hasta 65 segundos por el cierre ordenado del contenedor. SQLite conserva el volumen remoto y aplica migraciones inmutables registradas en `schema_migrations`; el deploy crea backup antes de reemplazar la imagen. `MigrateData` sigue siendo la unica accion que reemplaza una SQLite remota con la base local.
- `chat_settings.announcements_enabled` empieza en activo, migra con grupos convertidos a supergrupos y se configura desde `/config` en privados, grupos y supergrupos. Los canales reciben anuncios por defecto; Telegram no permite una UI de callback administrable desde un channel post sin un usuario efectivo.
- Los gastos no son configurables por grupo: `/gasto`, `/ultimosgastos`, `/estadogastos` y `/sincronizargastos` exigen nivel `DEV` y funcionan en cualquier chat. No se sugieren por BotFather. Los botones heredados `config:command:gastos` y `config:set:gastos:*` eliminan el mensaje al interactuar.
- Los rankings usan nombres visibles cacheados en `users` y user IDs; no generan menciones ni hacen requests de nombres al renderizar.
- La tabla de Galerazas usa ranking competitivo: empates comparten posicion y la siguiente posicion salta por la cantidad de usuarios anteriores. Las filas empatadas usan un guion y relleno del ancho de la posicion para alinear los nombres dentro de cada longitud de posicion; excepto en la primera fila de una pagina posterior, donde se repite la posicion para que la pagina sea autosuficiente. Si no hay puntajes, muestra un estado vacio localizado.
- Las traducciones se validan contra mojibake UTF-8 (`Ã`, `Â`, U+FFFD); usar escapes Unicode en textos nuevos cuando se necesite evitar conversiones de editor o consola.
- Todas las pantallas de `/config` incluyen `config:close`; los permisos se validan antes de ejecutar cualquier callback. El selector de idioma agrupa cuatro opciones por fila para mantener el tablero compacto.
- Cerrar el panel de control apaga el arbol de procesos local del bot antes de destruir la ventana.
- El panel marca sus procesos con `GALERAZO_PANEL_MANAGED=1`; cada inicio del bot actualiza `data/bot.pid`, incluido un relanzamiento local por `/reiniciarbot` en Windows. Durante el relevo se usa `data/bot.restart`: el panel muestra `REINICIANDO` y no elimina un PID que el hijo todavia esta publicando.
- `Galerazo Bot - Logs.lnk` abre PowerShell con `-NoExit` y sigue los logs remotos por IAP; `Ctrl+C` detiene la lectura sin modificar produccion.
- El runtime registra desde `DEBUG`. Un filtro global elimina exclusivamente los requests `httpx` exitosos de `getUpdates`; conserva otros requests, fallos y logs de aplicacion.
- Los niveles se validan al invocar comandos o tocar botones, no como clasificacion global permanente.
- La media se modera solo al crear triggers. Sin clave se omite; con clave, un fallo impide guardar ese intento. Los buffers y frames se mantienen en memoria y se limpian siempre.

## Git y deploy

- Repositorio remoto: `https://github.com/ldebortoli/galerazo-telegram-bot.git`.
- Rama principal: `main`, con tracking de `origin/main`.
- El flujo historico del proyecto usa commits directos a `main`; usar ramas `codex/<nombre>` si un trabajo futuro requiere PR o aislamiento.
- Antes de cerrar una sesion, actualizar `.codex/`, validar, committear y pushear si el remoto sigue configurado.
- No activar `.github/workflows/deploy.yml` hasta que el usuario lo pida explicitamente y existan los secrets de Railway.
- El camino recomendado de produccion es GCE + Docker Compose + Artifact Registry. Construir/publicar localmente es el default para no consumir Actions; GitHub solo publica imagenes por `workflow_dispatch`.
- Las correcciones ordinarias se validan, commitean y pushean sin publicar Artifact Registry ni desplegar GCE. Los releases se agrupan y requieren un pedido explicito del usuario en la instruccion actual; un bug de produccion no concede esa autorizacion. Docker local se construye solo si la superficie cambiada necesita validacion de contenedor.
- Todo release, deploy y rollback de Galerazo se opera desde la vista Deploy de Bot Control Center. Para una version nueva usar `Publicar y deployar`, despues de `Verificar`; usar `Deployar ultima imagen` solo para reutilizar una imagen ya publicada. No guiar al usuario por PowerShell salvo que Bot Control Center falle y lo solicite expresamente.
- El proyecto GCP personal para la flota es `bot-fleet-production`; cada bot conserva VM/contenedor, service account, datos y secretos con nombres especificos. Un proyecto separado se reserva para clientes, facturacion o permisos que requieran aislamiento fuerte.
- En `bot-fleet-production` estan habilitadas las APIs de Compute Engine, Artifact Registry, IAP, IAM Service Account Credentials y Cloud Storage. El registro Docker compartido para la flota es `bots` en `us-central1`; cada bot usa su propio nombre de imagen.
- BigQuery API esta habilitada, pero todavia no existe ningun dataset ni exportacion de Billing. No crear el dataset sin `-AcknowledgeBillableResource`; despues se debe habilitar manualmente el costo de uso estandar y esperar la tabla.
- La imagen mas reciente de Galerazo es `galerazobot:73ac112`, Linux/amd64, digest `sha256:18b077bb2e8d02aee579484223e8e821a390a56b9cea5e981b137c52c51a86ec`. Reemplaza para deploy a `f9df2b1`; `deploy/out/last-image.txt` conserva localmente la referencia mas reciente y esta ignorado por Git.
- `galerazo-vm` es la identidad de runtime de Galerazobot: esta habilitada, tiene `roles/artifactregistry.reader` sobre `bots` y `roles/storage.objectCreator` sobre el bucket privado de backups, ningún rol directo a nivel proyecto y cero claves administradas por el usuario. La cuenta local activa tiene `roles/artifactregistry.writer` solo sobre `bots`.
- La infraestructura de Galerazobot usa VPC custom `bot-fleet`, subred `bots-us-central1` dual-stack externa `10.20.0.0/24`, Private Google Access y una unica regla de esa VPC: SSH tcp/22 desde IAP hacia el tag `iap-ssh`. `galerazo-prod` es `e2-micro` en `us-central1-a`, Debian 12, 30 GB `pd-standard`, sin IPv4 externa, con IPv6 efimera, OS Login, Shielded VM y deletion protection.
- El host `galerazo-prod` ejecuta `galerazobot:73ac112` mediante Compose con `network_mode: host` para reutilizar la salida IPv6 de la VM. El contenedor esta `running/healthy`, Telegram mantiene polling y envios HTTP 200, la politica de reinicio es `unless-stopped` y Docker esta activo/habilitado. `bot.env` permanece root/0600 sin OpenAI/Google Sheets y SQLite esta instalado como 10001:10001/0600, legible e integro.
- Los backups SQLite mensuales de la flota usan `bot-fleet-production-sqlite-backups` en `us-central1`, acceso uniforme, prevención de acceso público, soft delete de siete días y ciclo de vida de 400 días bajo `bots/<bot-id>/`. Cada VM ejecuta una copia consistente con SHA-256 mediante un timer systemd persistente y sólo puede crear objetos. Galerazobot tiene una primera copia remota verificada y estado local en `/srv/galerazo/backups/monthly`.
- En el bucket compartido, `bots/<bot-id>/` es aislamiento lógico y no una frontera IAM: las VMs personales comparten confianza y `storage.objectCreator` a nivel bucket. Bots de clientes o dominios no confiables deben usar bucket o proyecto separado.
