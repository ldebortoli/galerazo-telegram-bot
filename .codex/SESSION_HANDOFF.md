# Session handoff

## Objetivo general

Mantener y ampliar Galerazo Bot como bot de Telegram modular y reanudable, con SQLite como fuente de verdad y el mismo runtime reproducible en Windows, CI y Docker.

## Tarea actual

No hay tareas autonomas en curso. Solo quedan los bloqueos externos de Google Sheets real y activacion explicita de Railway.

## Estado actual

- Rama `main`, tracking `origin/main`.
- Python 3.14.6 esta instalado en Windows y `.venv` fue creado con esa version.
- `.python-version`, Docker y GitHub Actions usan Python 3.14.6 exacto.
- El alias global `python` de la terminal existente puede resolver 3.13; usar `.venv\Scripts\python.exe` o activar `.venv`. El bot rechaza un runtime distinto.
- Dependencias directas actuales: python-telegram-bot 22.8, python-dotenv 1.2.2, gspread 6.2.1, google-auth 2.55.2 y tzdata 2026.3.
- `requirements.txt` fija tambien todas las dependencias transitivas y `pip list --outdated` devuelve una lista vacia.
- El lanzador compilado prioriza `.venv\Scripts\pythonw.exe`.
- `scripts/sync_windows_runtime.ps1` fue probado de punta a punta y recrea/valida el entorno local desde `.python-version`.
- Quality prueba Python nativo y Docker; Runtime Update busca estables semanalmente y fusiona solo despues de validar.
- Railway continua desactivado.
- `.env` sigue ignorado y nunca debe imprimirse ni versionarse.
- El panel abierto usa un ICO multirresolucion DIB valido; el icono pequeno leido desde `WM_GETICON` muestra el conejo con galera.
- El canal de logging esta verificado como accesible en `data/integration-status.json`.
- `/ruletarusa`, triggers ampliados, prefijos, help agrupado, debug JSON y listas sin menciones estan implementados.
- La Galeraza usa el timestamp Telegram con timezone argentino y el bot fue reiniciado con ese codigo bajo PID de control `10416`.
- `PerChatUpdateProcessor` serializa FIFO cada chat, permite que chats distintos avancen en paralelo y conserva el orden durante migraciones del ID de grupo al de supergrupo.
- `try_award_daily_galeraza` usa `BEGIN IMMEDIATE` ademas de la clave unica por chat/fecha.
- El ganador historico de Dankgentina del 2026-07-11 fue corregido a [Lewito] Leonardo (360780605), mensaje 1337843, timestamp Telegram `2026-07-11T03:08:17+00:00`; backup previo en `data/backups/galerazo-backup-20260711-030434.sqlite3`.
- El panel Galerazo fue reabierto con cierre propietario del bot; Spider Tracker recibio la misma politica y fue pusheado en `cc17958`.
- La base real ya tiene `galeraza_daily_winners.message_date` y `triggers.payload_json`.
- Los seis pedidos nuevos de USER_QUEUE estan implementados y probados.
- Los cambios funcionales fueron pusheados en `56c7aaf` y la prueba portable de panel en `493c815`.
- La regla global exige que cada tarea procesada de USER_QUEUE quede DONE, IN PROGRESS o con bloqueo inline; tambien se actualizo el inicializador de proyectos futuros.

## Validacion reciente

- `.venv\Scripts\python.exe --version`: Python 3.14.6.
- `python scripts/runtime_versions.py`: runtime alineado.
- `python -m unittest discover -s tests -v`: 59 pruebas OK.
- `python -m compileall app.py control_panel.py galerazo_bot scripts`: OK.
- `python -m pip check`: sin dependencias rotas.
- `python -m pip list --outdated --format=json`: `[]`.
- Lanzador Galerazo recompilado correctamente.
- Checkpoint posterior al reinicio PID 10416: bytes 172406..179931 sin errores nuevos.
- GitHub Actions Quality `29141960498`: success, incluidos build y 54 tests en Docker.
- GitHub Actions Deploy: skipped intencionalmente.

## Proximos pasos

1. Mantener bloqueados Google Sheets real y Railway hasta recibir el input correspondiente.

## Riesgos y bloqueos

- Docker no esta instalado localmente; la imagen y la suite se validaron correctamente en GitHub Actions.
- La creacion/fusion automatica de PRs depende de que el repositorio permita `GITHUB_TOKEN` con `contents` y `pull-requests` write; un fallo deja `main` sin cambios.
- No activar Railway ni exponer `.env` o credenciales.
- Google Sheets real esta bloqueado hasta que el usuario confirme spreadsheet ID, worksheet y credenciales de service account.
- Railway esta bloqueado por decision explicita: solo se activa cuando el usuario lo pida y existan sus secrets.

## Archivos principales modificados

- `.python-version`
- `requirements.in`
- `requirements.txt`
- `Dockerfile`
- `.dockerignore`
- `.github/workflows/quality.yml`
- `.github/workflows/runtime-update.yml`
- `.github/workflows/deploy.yml`
- `scripts/runtime_versions.py`
- `galerazo_bot/runtime.py`
- `galerazo_bot/telegram_bot.py`
- `galerazo_bot/update_processor.py`
- `galerazo_bot/database.py`
- `galerazo_bot/control_panel.py`
- `launcher/GalerazoBotControlLauncher.cs`
- `README.md`
- `AGENTS.md`
- `tests/test_runtime_versions.py`
- `scripts/build_windows_icon.ps1`
- `assets/galerazo-bot-icon.ico`
- `build_control_panel.ps1`
- `tests/test_windows_icon.py`
- `tests/test_update_processor.py`
- `tests/test_galeraza.py`
