# Galerazo Bot - Contexto del proyecto

## Descripcion general

Galerazo Bot es un bot de Telegram para chats privados, grupos, supergrupos y canales. Incluye administracion por niveles, listas paginadas, configuracion por chat, un juego diario llamado La Galeraza, triggers, registro de gastos con sincronizacion opcional a Google Sheets y un panel de control local para Windows.

La fuente de verdad operativa para agentes es esta carpeta `.codex/`. Al iniciar una sesion se deben leer, en orden: `CONTEXT.md`, `DECISIONS.md`, `BACKLOG.md`, `USER_QUEUE.md` y `SESSION_HANDOFF.md`.

La misma politica se aplica globalmente desde `C:\Users\calei\.codex\AGENTS.md`. Los proyectos nuevos se inicializan con `C:\Users\calei\.codex\project-memory\Initialize-ProjectMemory.ps1` antes de implementar su primera tarea.

## Stack tecnologico

- Python 3.12 en Docker; desarrollo local verificado con Python 3.13 en Windows.
- `python-telegram-bot==22.3` para Telegram Bot API y polling.
- SQLite mediante `sqlite3` de la libreria estandar.
- `gspread` y `google-auth` para Google Sheets.
- `python-dotenv` para configuracion local desde `.env`.
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
- `galerazo_bot/expenses.py` y `google_sheets.py`: gastos, formato y sincronizacion.
- `galerazo_bot/control_panel.py`: UI local, manejo del proceso, `.env` y logs.
- `launcher/GalerazoBotControlLauncher.cs`: lanzador Windows.
- `assets/`: PNG e ICO del conejo con galera.
- `tests/`: pruebas `unittest` de regresion y comportamiento.
- `.github/workflows/deploy.yml`: deploy Railway desactivado con `if: ${{ false }}`.

## Persistencia y consistencia

- La base por defecto es `data/galerazo.sqlite3`.
- Cada operacion abre una conexion corta mediante un context manager y garantiza commit/rollback y cierre explicito.
- Todos los datos asociados a un `chat_id` deben migrarse cuando Telegram convierte un grupo en supergrupo.
- `Database.migrate_chat_id` es el punto central de esa migracion.
- El bot usa `concurrent_updates(False)` para procesar updates secuencialmente.
- Los callbacks de botoneras se procesan en el mismo flujo secuencial.
- La Galeraza usa una insercion atomica para garantizar un ganador por chat y dia.
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

`.env`, credenciales, bases, backups, logs y PID locales no se versionan.

## Comandos importantes de desarrollo

Instalar:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

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

Validaciones disponibles:

```powershell
python -m compileall app.py control_panel.py galerazo_bot
python -m galerazo_bot.cli hola
python -m galerazo_bot.cli help
python -m galerazo_bot.cli nivel
python -m unittest discover -s tests -v
git diff --check
```

La suite automatizada usa `unittest`. Actualmente cubre el enrutamiento de comandos; para persistencia y panel se mantienen ademas pruebas focalizadas con bases SQLite temporales y flujo de proceso.

## Convenciones de codigo

- ASCII por defecto en archivos nuevos.
- Handlers y auxiliares especificos de un comando viven juntos en `command_handlers/<grupo>.py`.
- Registrar cada modulo nuevo en `command_handlers/__init__.py`.
- Reutilizar APIs de `python-telegram-bot` antes de implementar equivalentes propios.
- Las listas de usuarios muestran siempre el user ID entre parentesis.
- Las listas largas usan la paginacion reutilizable y nunca cortan un renglon.
- Los comandos conservan sus nombres originales en todos los idiomas.
- Los comandos inexistentes se ignoran silenciosamente; no registrar fallbacks en grupos posteriores de PTB que vuelvan a procesar comandos validos.
- Los rankings usan nombres visibles cacheados en `users` y user IDs; no generan menciones ni hacen requests de nombres al renderizar.
- Todas las pantallas de `/config` incluyen `config:close`; los permisos se validan antes de ejecutar cualquier callback.
- Los niveles se validan al invocar comandos o tocar botones, no como clasificacion global permanente.

## Git y deploy

- Repositorio remoto: `https://github.com/ldebortoli/galerazo-telegram-bot.git`.
- Rama principal: `main`, con tracking de `origin/main`.
- El flujo historico del proyecto usa commits directos a `main`; usar ramas `codex/<nombre>` si un trabajo futuro requiere PR o aislamiento.
- Antes de cerrar una sesion, actualizar `.codex/`, validar, committear y pushear si el remoto sigue configurado.
- No activar `.github/workflows/deploy.yml` hasta que el usuario lo pida explicitamente y existan los secrets de Railway.
