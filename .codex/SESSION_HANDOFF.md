# Session handoff

## Objetivo general

Mantener y ampliar Galerazo Bot como bot de Telegram modular, consistente y reanudable, con SQLite como fuente de verdad, migracion completa de `chat_id` y operacion local/deploy documentados.

## Tarea actual

No hay una tarea activa. El bug de doble respuesta de comandos esta corregido y cubierto por pruebas.

## Estado real al cerrar la sesion

- Rama: `main`, tracking `origin/main`.
- `86cbc12 Add group expense tracking` y `023c4fa Add persistent project memory and bot control panel` fueron pusheados a `origin/main`.
- Despues de actualizar este handoff debe existir solo un commit final de estado y `main` debe quedar sincronizada con origin.
- El panel local esta abierto, pero el bot local esta apagado y no existe `data/bot.pid`. El ultimo proceso termino porque otra instancia uso el mismo token para `getUpdates`; no reiniciar a ciegas hasta identificarla.
- `.env` existe localmente y contiene secretos; esta ignorado y nunca debe imprimirse ni versionarse.
- El workflow de Railway sigue desactivado intencionalmente.
- `C:\Users\calei\.codex\AGENTS.md` contiene las reglas globales y sera cargado en nuevos runs de Codex.
- `C:\Users\calei\.codex\project-memory\Initialize-ProjectMemory.ps1` inicializa proyectos nuevos sin sobrescribir memoria existente.

## Terminado recientemente

- Se elimino el fallback PTB de comandos desconocidos en grupo 2 y el dispatcher ahora retorna `None` para nombres inexistentes.
- `/galerazas` se registra una sola vez y ya no genera una segunda respuesta `unknown_command`.
- Se agrego `tests/test_command_routing.py`; sus tres pruebas y `compileall` pasan.
- Se instalo la politica global de memoria y el inicializador idempotente para proyectos futuros.
- Se inicializo `.codex/` en los proyectos activos nombrados y repositorios reales detectados, excluyendo carpetas fechadas efimeras y `CODEX APPS`.
- La carga automatica de `~/.codex/AGENTS.md` fue verificada contra la documentacion oficial de Codex.
- Se validaron cinco archivos de memoria y marcador `AGENTS.md` en 14 proyectos: New project, Spider Tracker, Content Generator, Documentos de vacaciones, Galerazo Bot, INA, Liricas, Presentacion de tesis, Licenciado Dengue Web, Reshare Stories, Pixel Flow Matrix, Viajes planeados, Seguidores de Instagram y Catalogo de obras.
- Commits pusheados: Spider Tracker `fbf2a93`, Documentos de vacaciones `0f547ee`, Reshare Stories `1260ab5` y Seguidores `d1e9100`.
- Commits locales sin remoto: Pixel Flow `0740ed8` y Catalogo de obras `158b870`.
- Sistema de gastos por grupo con SQLite y sincronizacion opcional a Google Sheets.
- Panel Tkinter con control de proceso, editor de `.env` y visor de logs.
- Lanzador C# y acceso directo `Galerazo Bot` en `C:\Users\calei\Documents\Codex\CODEX APPS`.
- Icono PNG/ICO de conejo con galera.
- Diagnostico del fallo de encendido: faltaba `python-dotenv` y una instancia vieja no pasaba el entorno.
- El panel ahora pasa `.env` al hijo, valida errores tempranos y usa APIs Win32 no destructivas para comprobar PIDs.
- El flujo real de botones Apagar/Encender termino en `BOT ENCENDIDO` sin errores.
- Las conexiones SQLite ahora se cierran explicitamente; migracion, backup y limpieza temporal fueron validados.
- Se creo la memoria persistente `.codex/` y `AGENTS.md` obliga a cargarla al iniciar.
- Validaciones finales: compileall, `pip check`, CLI `hola`/`nivel`, migracion de gastos, backup SQLite, limpieza temporal, deteccion Win32 de proceso y `git diff --check`.

## Proximos pasos exactos

1. Procesar el proximo pedido del usuario desde `USER_QUEUE.md`/`BACKLOG.md`.
2. Antes de encender localmente, resolver la instancia duplicada que usa el token de Telegram.
3. El proximo trabajo funcional priorizado sigue siendo conectar el Google Sheet real cuando se proporcionen sus datos.

## Problemas y riesgos

- No hay suite formal de tests; la cobertura actual es compileall y scripts focalizados.
- El primer barrido global encontro repositorios sin remoto `origin`; el inicializador fue corregido y la repeticion idempotente termino correctamente.
- Las instrucciones globales se descubren una vez por run; esta sesion comenzo antes del cambio, pero todos los runs futuros las cargaran.
- Los proyectos sin Git conservan la memoria solo localmente. Pixel Flow y Catalogo tienen commit pero no remoto.
- Reshare Stories y Seguidores mantienen cambios locales preexistentes fuera de los commits de memoria; no revertirlos ni mezclarlos accidentalmente.
- Nunca usar `os.kill(pid, 0)` para comprobar procesos en Windows; ver D-011.
- Antes de terminar procesos, leer y validar el PID exacto. No ejecutar operaciones contra PID 0 si falta `data/bot.pid`.
- Dos instancias del bot causan conflictos de polling. Mantener una sola instancia local.
- Telegram devuelve `Chat not found` para el canal de logging configurado; revisar ID y permisos antes de dar por valida esa integracion.
- No activar deploy automatico ni transmitir `.env`/credenciales.
- La guia README contiene algunos caracteres mojibake preexistentes en la seccion de configuracion; no se corrigieron aun porque no bloquean la funcionalidad.

## Archivos modificados o nuevos en esta linea de trabajo

- `.codex/CONTEXT.md`
- `.codex/DECISIONS.md`
- `.codex/BACKLOG.md`
- `.codex/USER_QUEUE.md`
- `.codex/SESSION_HANDOFF.md`
- `AGENTS.md`
- `.gitignore`
- `README.md`
- `requirements.txt`
- `control_panel.py`
- `galerazo_bot/control_panel.py`
- `build_control_panel.ps1`
- `launcher/GalerazoBotControlLauncher.cs`
- `assets/galerazo-bot-icon.png`
- `assets/galerazo-bot-icon.ico`
- Archivos del sistema de gastos incluidos en el commit local `86cbc12`.
- `galerazo_bot/database.py` para cierre explicito de conexiones SQLite.
