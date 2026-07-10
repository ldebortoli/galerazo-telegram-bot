# Session handoff

## Objetivo general

Mantener y ampliar Galerazo Bot como bot de Telegram modular y reanudable, con SQLite como fuente de verdad, migracion completa de `chat_id` y operacion local/deploy documentados.

## Tarea actual

No hay una tarea activa. Todos los pedidos registrados en `USER_QUEUE.md` estan implementados, validados y en `DONE`.

## Estado actual

- Rama `main`, tracking `origin/main`.
- La politica global ejecuta automaticamente tareas originadas en `USER_QUEUE.md` hasta completarlas o bloquearlas; se propago a 14 proyectos activos y al inicializador de proyectos futuros.
- El bot y el panel Galerazo tienen exclusividad local; Spider Tracker comparte un mutex entre sus paneles C# y PowerShell.
- `/debug` serializa `Update.to_dict()`, los errores no manejados incluyen Update JSON y los logs redactan tokens.
- `python -m galerazo_bot.log_checkpoint` esta inicializado y no reporta entradas pendientes.
- `/help` usa `/comando`, existe `/start` bilingue y polling conserva updates pendientes con `drop_pending_updates=False`.
- El panel carga el icono del conejo, usa AppUserModelID propio y agranda la pestana seleccionada.
- El bot local permanece apagado; no iniciar a ciegas si existe un deploy externo con el mismo token.
- `.env` existe, esta ignorado y nunca debe imprimirse ni versionarse.
- Railway sigue desactivado intencionalmente.

## Validacion reciente

- `python -m unittest discover -s tests -v`: 19 pruebas OK.
- `python -m compileall app.py control_panel.py galerazo_bot`: OK.
- Runtime Tkinter: padding `(20, 11)`, fuente seleccionada `Segoe UI Semibold 11`, icono cargado.
- Lanzador Galerazo y panel Spider recompilados correctamente.
- Parser PowerShell de Spider: OK.
- Checkpoint de log: sin entradas nuevas pendientes.

## Proximos pasos

1. Atender el proximo pedido directo o pendiente nuevo de `USER_QUEUE.md`.
2. Para habilitar logging remoto, corregir `TELEGRAM_LOG_CHAT_ID` y asegurar que el bot sea miembro/admin del canal; el valor actual responde `Chat not found`.
3. Conectar el Google Sheet real cuando el usuario confirme ID, hoja y credenciales.

## Riesgos y bloqueos

- El canal de logging no es accesible con la configuracion actual (`Chat not found`); requiere un cambio externo de ID o permisos.
- Telegram no expone que equipo o servicio mantiene un `getUpdates`; el mutex identifica duplicados locales y el error identifica conflictos externos.
- No activar deploy automatico ni transmitir `.env` o credenciales.
- Reshare Stories y Seguidores conservan cambios locales ajenos; no mezclarlos ni revertirlos.

## Archivos principales modificados

- `C:\Users\calei\.codex\AGENTS.md`
- `C:\Users\calei\.codex\project-memory\Initialize-ProjectMemory.ps1`
- `AGENTS.md`
- `.codex/*`
- `galerazo_bot/instance_lock.py`
- `galerazo_bot/log_checkpoint.py`
- `galerazo_bot/logging_utils.py`
- `galerazo_bot/telegram_bot.py`
- `galerazo_bot/control_panel.py`
- `galerazo_bot/command_handlers/help.py`
- `galerazo_bot/command_handlers/start.py`
- `galerazo_bot/i18n.py`
- `tests/*`
