# Session handoff

## Objetivo general

Mantener y ampliar Galerazo Bot como bot de Telegram modular y reanudable, con SQLite como fuente de verdad y el mismo runtime reproducible en Windows, CI y Docker.

## Tarea actual

No hay tareas autonomas en curso. Quedan bloqueados Google Sheets real, Railway y la comprobacion visual del medio de pago de GitHub.

## Estado actual

- Rama `main`, tracking `origin/main`.
- Python 3.14.6 esta instalado en Windows y `.venv` fue creado con esa version.
- `.python-version`, Docker y GitHub Actions usan Python 3.14.6 exacto.
- El alias global `python` de la terminal existente puede resolver 3.13; usar `.venv\Scripts\python.exe` o activar `.venv`. El bot rechaza un runtime distinto.
- Dependencias directas actuales: python-telegram-bot 22.8, python-dotenv 1.2.2, gspread 6.2.1, google-auth 2.56.0 y tzdata 2026.3. El lock tambien fija anyio 4.14.2.
- `requirements.txt` fija tambien todas las dependencias transitivas y `pip list --outdated` devuelve una lista vacia.
- El lanzador compilado prioriza `.venv\Scripts\pythonw.exe`.
- `scripts/sync_windows_runtime.ps1` fue probado de punta a punta y recrea/valida el entorno local desde `.python-version`.
- Quality prueba Python en Linux; Docker Quality valida el contenedor cuando cambia su runtime; Runtime Update busca estables semanalmente y publica un commit normal en `main` solo despues de validar entorno nativo y Docker.
- Quality quedo reducido a un job Linux por cambio sustantivo; Docker corre por separado solo ante cambios de runtime/contenedor, y commits documentales no disparan CI.
- Railway continua desactivado.
- `.env` sigue ignorado y nunca debe imprimirse ni versionarse.
- Al iniciar la investigacion de hosting del 2026-07-19 no habia `data/bot.pid` ni proceso administrado del bot activo. El panel y el bot que figuraban en el handoff anterior ya no estaban en ejecucion. El panel usa un ICO con nueve capas DIB BGRA de 32 bits; las capas 16..64 usan composicion compacta y el icono 16x16 activo ocupa 14x14 con margen transparente uniforme de un pixel.
- El panel abre en 760x720 (minimo 680x700); el label de logging recibe sus 21 px requeridos y muestra completo `Canal de logging: OK - Canal de logging accesible.`
- El canal de logging esta verificado como accesible en `data/integration-status.json`.
- `/ruletarusa`, triggers ampliados, prefijos, help agrupado, debug JSON y listas sin menciones estan implementados.
- La Galeraza usa el timestamp Telegram con timezone argentino. Todo mensaje original con usuario humano compite, incluidos eventos de servicio como altas al chat; bots, ediciones y updates sin usuario no compiten.
- El usuario confirmo que no hace falta corregir retroactivamente el evento de servicio omitido antes de este arreglo; no existe una tarea pendiente por ese punto.
- `PerChatUpdateProcessor` serializa FIFO cada chat, permite que chats distintos avancen en paralelo y conserva el orden durante migraciones del ID de grupo al de supergrupo.
- `try_award_daily_galeraza` usa `BEGIN IMMEDIATE` ademas de la clave unica por chat/fecha.
- El ganador historico de Dankgentina del 2026-07-11 fue corregido a [Lewito] Leonardo (360780605), mensaje 1337843, timestamp Telegram `2026-07-11T03:08:17+00:00`; backup previo en `data/backups/galerazo-backup-20260711-030434.sqlite3`.
- El panel Galerazo fue reabierto con cierre propietario del bot; Spider Tracker recibio la misma politica y fue pusheado en `cc17958`.
- La base real ya tiene `galeraza_daily_winners.message_date` y `triggers.payload_json`.
- Los seis pedidos nuevos de USER_QUEUE estan implementados y probados.
- Los cambios funcionales fueron pusheados en `56c7aaf` y la prueba portable de panel en `493c815`.
- La regla global exige que cada tarea procesada de USER_QUEUE quede DONE, IN PROGRESS o con bloqueo inline; tambien se actualizo el inicializador de proyectos futuros.
- La investigacion de hosting del 2026-07-19 confirmo que no hacen falta dominio, IP publica ni puertos entrantes: el polling solo requiere salida a Internet, un proceso siempre activo y persistencia para SQLite. La base real ocupa 172032 bytes, todos los archivos locales bajo `data` 856990 bytes y una sonda local de solo importacion uso 54,2 MiB de RAM.
- Opciones investigadas sin activar ningun deploy: Google Compute Engine `e2-micro` puede quedar en USD 0 con IPv6 y 30 GB persistentes; Railway Hobby cuesta USD 5/mes y es el despliegue mas simple para el repositorio; Fly.io con 256 MB mas 1 GB persistente ronda USD 2,17/mes en una region economica; DigitalOcean parte de USD 4/mes y el backup semanal agrega 20%; hardware domestico solo mejora claramente el costo si ya existe o se amortiza durante varios anos. Railway Free tiene solo USD 1/mes de credito y queda demasiado cerca del consumo estimado para prometer 24/7; Oracle Always Free puede recuperar instancias ociosas.

## Validacion reciente

- La investigacion de hosting del 2026-07-19 paso `runtime_versions.py`, las 64 pruebas y `git diff --check`. El checkpoint detecto dos `502 Bad Gateway` transitorios de la API de Telegram ocurridos el 2026-07-16 durante `getUpdates`; el polling recupero respuestas `200 OK` inmediatamente, por lo que no quedo un defecto local ni perdida persistente que corregir.
- `.venv\Scripts\python.exe --version`: Python 3.14.6.
- `python scripts/runtime_versions.py`: runtime alineado.
- `python -m unittest discover -s tests -v`: 64 pruebas OK, incluida la auditoria de las 46 categorias de `StatusUpdate`, la ruta para pin/altas/bajas y la geometria Tk nativa de Windows.
- `python -m compileall app.py control_panel.py galerazo_bot scripts`: OK.
- `python -m pip check`: sin dependencias rotas.
- `python -m pip list --outdated --format=json`: `[]`.
- Lanzador Galerazo recompilado correctamente.
- Acceso `CODEX APPS\\Galerazo Bot.lnk` actualizado al ICO corregido; el bot siguio activo bajo PID `10416` durante el reinicio del panel.
- Checkpoint posterior al reinicio PID 10416: bytes 172406..179931 sin errores nuevos.
- GitHub Actions Quality `29169437187`: success con un unico job Linux; el test visual Tk se ejecuta localmente en Windows y se omite en Linux.
- GitHub Actions Docker Quality `29142895267`: success; se disparo una vez por la creacion del workflow y en adelante solo corre para cambios de runtime/contenedor.
- El push `f58718a` no genero ningun run de Deploy; el workflow desactivado quedo exclusivamente manual.
- El push documental `fbde709` genero cero runs, confirmando que `.codex`/Markdown ya no consumen Actions.
- Checkpoint mas reciente: no habia entradas posteriores al rango 249232..249957, ya revisado sin errores.
- El run semanal `29249239004` del 2026-07-13 habia validado entorno y Docker, pero fallo porque el repositorio no permitio crear el PR automatico. El workflow ahora publica un commit normal en `main` despues de validar y tiene una prueba contra regresiones de permisos/force push.
- `anyio` 4.14.2 y `google-auth` 2.56.0 quedaron instalados y bloqueados. Validacion: 61 pruebas locales OK, compileall OK, runtime alineado, `pip check` OK y `pip list --outdated` vacio.
- Commit funcional `b8361e5` pusheado. Quality `29279845566` paso; Docker Quality `29279845453` encontro un HTTP 500 transitorio de Docker Hub y su reejecucion aislada paso completa.
- La rama remota temporal `automation/runtime-update` que habia dejado el run fallido fue eliminada despues de validar `main`.
- Cambio funcional pusheado en `700811d`; Quality `29460027552` paso con el unico job Linux esperado.
- Checkpoint posterior al reinicio final PID 19352: bytes 258111..258936 sin errores nuevos.
- Cobertura exhaustiva pusheada en `07e7514`; las 64 pruebas locales y Quality `29460516323` pasaron. El checkpoint 259236..264136 no encontro errores y el bot siguio activo bajo PID 19352.
- Checkpoint posterior a la confirmacion: bytes 264436..264836 sin errores nuevos.

## Proximos pasos

1. Para confirmar el medio de pago, iniciar sesion en GitHub en el navegador disponible o autorizar explicitamente `gh auth refresh -h github.com -s user`; no ampliar scopes sin confirmacion.
2. Mantener bloqueados Google Sheets real y Railway hasta recibir el input correspondiente.

## Riesgos y bloqueos

- Docker no esta instalado localmente; la imagen y la suite se validaron correctamente en GitHub Actions.
- Runtime Update hace un push normal despues de validar; si `main` avanza durante el job, el push se rechaza sin sobrescribir cambios.
- No activar Railway ni exponer `.env` o credenciales.
- Google Sheets real esta bloqueado hasta que el usuario confirme spreadsheet ID, worksheet y credenciales de service account.
- Railway esta bloqueado por decision explicita: solo se activa cuando el usuario lo pida y existan sus secrets.
- Facturacion personal GitHub no se pudo leer: la API devolvio 404 por falta de scope `user` y la sesion web disponible estaba deslogueada. Segun GitHub, sin medio de pago valido se bloquea el uso al agotar la cuota.

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
