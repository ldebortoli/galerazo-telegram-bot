# Session handoff

## Objetivo general

Mantener y ampliar Galerazo Bot como bot de Telegram modular y reanudable, con SQLite como fuente de verdad y el mismo runtime reproducible en Windows, CI y Docker.

## Tarea actual

No hay tarea activa. El runtime y las dependencias quedaron actualizados y validados localmente; falta confirmar los checks Docker de GitHub Actions despues del push.

## Estado actual

- Rama `main`, tracking `origin/main`.
- Python 3.14.6 esta instalado en Windows y `.venv` fue creado con esa version.
- `.python-version`, Docker y GitHub Actions usan Python 3.14.6 exacto.
- El alias global `python` de la terminal existente puede resolver 3.13; usar `.venv\Scripts\python.exe` o activar `.venv`. El bot rechaza un runtime distinto.
- Dependencias directas actuales: python-telegram-bot 22.8, python-dotenv 1.2.2, gspread 6.2.1 y google-auth 2.55.2.
- `requirements.txt` fija tambien todas las dependencias transitivas y `pip list --outdated` devuelve una lista vacia.
- El lanzador compilado prioriza `.venv\Scripts\pythonw.exe`.
- `scripts/sync_windows_runtime.ps1` fue probado de punta a punta y recrea/valida el entorno local desde `.python-version`.
- Quality prueba Python nativo y Docker; Runtime Update busca estables semanalmente y fusiona solo despues de validar.
- Railway continua desactivado.
- `.env` sigue ignorado y nunca debe imprimirse ni versionarse.

## Validacion reciente

- `.venv\Scripts\python.exe --version`: Python 3.14.6.
- `python scripts/runtime_versions.py`: runtime alineado.
- `python -m unittest discover -s tests -v`: 20 pruebas OK.
- `python -m compileall app.py control_panel.py galerazo_bot scripts`: OK.
- `python -m pip check`: sin dependencias rotas.
- `python -m pip list --outdated --format=json`: `[]`.
- Lanzador Galerazo recompilado correctamente.
- Docker local no esta instalado; confirmar build y tests con GitHub Actions.

## Proximos pasos

1. Pushear cambios y verificar ambos jobs del workflow Quality.
2. Si Docker falla por Python o dependencias, corregir o revertir esta actualizacion antes de darla por terminada.
3. Atender el proximo pedido o una entrada nueva de `USER_QUEUE.md`.

## Riesgos y bloqueos

- Docker no puede validarse en esta maquina porque el comando no esta instalado.
- La creacion/fusion automatica de PRs depende de que el repositorio permita `GITHUB_TOKEN` con `contents` y `pull-requests` write; un fallo deja `main` sin cambios.
- El canal de logging sigue respondiendo `Chat not found` hasta corregir ID/permisos externos.
- No activar Railway ni exponer `.env` o credenciales.

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
- `galerazo_bot/control_panel.py`
- `launcher/GalerazoBotControlLauncher.cs`
- `README.md`
- `AGENTS.md`
- `tests/test_runtime_versions.py`
