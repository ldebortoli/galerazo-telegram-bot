# Decisiones tecnicas

Este archivo es append-only a nivel conceptual: no borrar decisiones anteriores. Si una decision cambia, agregar una nueva entrada que indique cual reemplaza y por que.

## D-001 - python-telegram-bot como integracion Telegram

- Estado: vigente.
- Fecha registrada: 2026-07-10 (decision preexistente).
- Decision: usar `python-telegram-bot` y sus handlers oficiales en lugar de una implementacion HTTP propia.
- Motivo: reducir codigo propio, aprovechar tipos y metodos mantenidos por la libreria y conservar una arquitectura modular de dominio.

## D-002 - Procesamiento secuencial de updates

- Estado: vigente.
- Fecha registrada: 2026-07-10 (decision preexistente).
- Decision: configurar `ApplicationBuilder.concurrent_updates(False)`.
- Motivo: preservar orden causal entre mensajes, callbacks, escrituras SQLite y comandos que leen listas; es critico para La Galeraza.
- Restriccion: no habilitar concurrencia global sin disenar y probar una estrategia equivalente de orden por chat.

## D-003 - SQLite como fuente persistente principal

- Estado: vigente.
- Fecha registrada: 2026-07-10 (decision preexistente).
- Decision: mantener SQLite como fuente de verdad del bot. Integraciones externas como Google Sheets son destinos secundarios sincronizables.
- Motivo: operacion simple, backups directos y consistencia local aun cuando una integracion externa no este configurada o falle.

## D-004 - Migracion integral de chat_id

- Estado: vigente.
- Fecha registrada: 2026-07-10 (decision preexistente).
- Decision: todo dato persistente asociado a un chat debe actualizarse en `Database.migrate_chat_id` cuando un grupo migra a supergrupo.
- Motivo: evitar duplicados, perdida logica de configuracion y rankings fragmentados.
- Restriccion: ninguna tabla nueva con `chat_id` se considera terminada hasta agregar y probar su migracion.

## D-005 - Tres niveles de permisos evaluados al usar comandos

- Estado: vigente.
- Fecha registrada: 2026-07-10 (decision preexistente).
- Decision: niveles `common`, `admin` y `dev`. Admin incluye administradores del chat y la persona que agrego el bot. La relevancia del nivel se limita a invocaciones de comandos y callbacks protegidos.
- Motivo: evitar restricciones globales innecesarias y reflejar permisos actuales de Telegram.
- Restriccion: todo intento de usar un comando sin nivel suficiente debe recibir error de permisos, salvo usuarios globalmente bloqueados, que son ignorados.

## D-006 - Modulos autocontenidos por comando

- Estado: vigente.
- Fecha registrada: 2026-07-10 (decision preexistente).
- Decision: cada conjunto de comandos vive en su archivo dentro de `galerazo_bot/command_handlers/`, junto con auxiliares especificos, y exporta `COMMANDS`.
- Motivo: agregar comandos modificando solo un modulo nuevo y el registro central.

## D-007 - Paginacion generica persistida

- Estado: vigente.
- Fecha registrada: 2026-07-10 (decision preexistente).
- Decision: cualquier respuesta de lista que exceda Telegram usa el componente generico de paginacion, con metadata SQLite, permisos, candado y eliminacion.
- Motivo: evitar implementaciones duplicadas y mensajes que excedan limites o corten renglones.
- Retencion: metadata de mas de dos semanas se elimina al iniciar o al interactuar.

## D-008 - Internacionalizacion de textos, no de comandos

- Estado: vigente.
- Fecha registrada: 2026-07-10 (decision preexistente).
- Decision: traducir todos los textos visibles entre espanol e ingles segun el chat, conservando los nombres originales de comandos.
- Motivo: compatibilidad y descubrimiento estable de comandos.
- Default: espanol.

## D-009 - Gastos local-first con Google Sheets opcional

- Estado: vigente.
- Fecha registrada: 2026-07-10.
- Decision: guardar cada gasto primero en SQLite y luego intentar escribirlo en Google Sheets con `gspread`.
- Motivo: no perder gastos cuando faltan credenciales, la hoja no esta configurada o Google falla.
- Estado de grupo: gastos deshabilitado por defecto y habilitable solo por nivel admin o dev; una vez habilitado, cualquier usuario del grupo puede registrar.

## D-010 - Panel local directo, Docker para deploy

- Estado: vigente.
- Fecha registrada: 2026-07-10.
- Decision: el panel de Windows administra un proceso Python local; no controla Docker. Docker queda para deployment.
- Implementacion: Tkinter, `data/bot.pid`, `data/bot.log` y lanzador C# sin consola.
- Motivo: control inmediato y simple para desarrollo local.

## D-011 - Consulta nativa de procesos en Windows

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: verificar PIDs con `OpenProcess` y `GetExitCodeProcess` en Windows; usar `os.kill(pid, 0)` solo fuera de Windows.
- Motivo: `os.kill(pid, 0)` produjo falsos negativos en Windows y hacia que el panel borrara `bot.pid` de un bot activo.

## D-012 - Deploy automatico preparado pero desactivado

- Estado: vigente.
- Fecha registrada: 2026-07-10 (decision preexistente).
- Decision: mantener el workflow Railway con `if: ${{ false }}`.
- Motivo: el usuario pidio preparar el pipeline sin hacerlo funcional todavia.

## D-013 - `.codex/` como memoria persistente del proyecto

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: `CONTEXT.md`, `DECISIONS.md`, `BACKLOG.md`, `USER_QUEUE.md` y `SESSION_HANDOFF.md` son la fuente de verdad para continuidad entre sesiones, modelos y agentes.
- Motivo: el proyecto no debe depender del historial del chat.
- Flujo obligatorio: leer los cinco archivos al iniciar; sincronizar USER_QUEUE con BACKLOG; actualizar backlog/handoff durante el trabajo; commit y push al cerrar si existe remoto.

## D-014 - Conexiones SQLite cortas y cierre explicito

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: `Database._connect` es un context manager que abre una conexion por operacion, hace commit o rollback y siempre cierra en `finally`.
- Motivo: `with sqlite3.Connection` maneja transacciones pero no cierra el descriptor; en Windows esto bloqueaba la limpieza de bases temporales y podia retener archivos mas tiempo del necesario.
- Validacion: migracion de gastos, creacion/reapertura de backup y limpieza de un directorio temporal.

## D-015 - Politica global de memoria para todos los proyectos

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: la estructura `.codex/` y su flujo obligatorio se aplican a todos los proyectos activos y deben inicializarse automaticamente antes del primer trabajo en cualquier proyecto futuro.
- Alcance: la instruccion global vive en `C:\Users\calei\.codex\AGENTS.md`; cada proyecto conserva su propia fuente de verdad en `.codex/`.
- Motivo: continuidad entre sesiones, modelos y agentes sin depender de memoria conversacional.
- Verificacion: la documentacion oficial de Codex confirma que al iniciar cada run carga primero el `AGENTS.md` global de `CODEX_HOME` y luego concatena las instrucciones del proyecto desde la raiz hacia el directorio actual.

## D-016 - Comandos desconocidos sin respuesta

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: ignorar silenciosamente comandos que no existen y no registrar un fallback PTB en un grupo posterior.
- Motivo: los handlers de distintos grupos pueden procesar el mismo update; el fallback de grupo 2 respondia `unknown_command` incluso despues de que `/galerazas` ya habia sido manejado correctamente en grupo 1.
- Validacion: pruebas para `/inventado`, `!inventado`, texto desconocido, registro unico de `/galerazas` y ausencia de handlers en grupo 2.

## D-017 - Cierre autorizado del menu de configuracion

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: todas las pantallas de `/config` incluyen una X con callback `config:close`; solo admines y devs pueden eliminar el mensaje.
- Motivo: permitir cerrar el tablero sin dejar botoneras obsoletas y conservar el mismo control de permisos de todas las opciones de configuracion.
- Validacion: presencia de X en los cuatro tipos de menu, parseo del callback, rechazo de common y cierre para admin/dev.

## D-018 - Ranking sin menciones y con nombres cacheados

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: el ranking se titula `Tabla de Galerazas` y muestra `display_name (user_id)`; si falta nombre visible usa el username sin `@` y finalmente `Usuario`.
- Motivo: evitar menciones/notificaciones y distinguir usuarios con nombres repetidos sin consultas adicionales a Telegram.
- Persistencia: la tabla `users` ya cachea y actualiza `display_name`/`username` al recibir updates; `get_galeraza_scores` resuelve todo con un JOIN local.

## D-019 - Ejecucion automatica de la cola del usuario

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: al comenzar un run, cada pedido pendiente de `USER_QUEUE.md` se incorpora sin duplicados a `BACKLOG.md`, se marca como procesado y luego se ejecuta automaticamente por prioridad hasta quedar completado o realmente bloqueado.
- Semantica: `Procesadas` solo confirma que la entrada fue incorporada al backlog; una tarea esta resuelta unicamente cuando figura en `DONE` despues de implementacion, validacion y documentacion.
- Continuidad: terminar el pedido directo que inicio el run no detiene el trabajo pendiente de la cola. Si una tarea se bloquea, se registra el bloqueo preciso y se continua con otras tareas ejecutables.
- Alcance: todos los proyectos activos y futuros mediante la politica global y el inicializador de memoria.

## D-020 - Exclusividad por token y por panel

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: el proceso Telegram toma un mutex derivado del token y el panel toma otro derivado del proyecto; una segunda instancia local se rechaza antes de iniciar.
- Conflictos externos: un `telegram.error.Conflict` detiene el proceso con un diagnostico que indica revisar otros equipos o deploys.
- Motivo: el archivo PID del panel no cubria ejecuciones directas de `app.py` ni otros lanzadores.

## D-021 - Checkpoint incremental y redaccion de logs

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: `python -m galerazo_bot.log_checkpoint` revisa solo bytes nuevos de `data/bot.log`; no avanza ante errores hasta recibir `--acknowledge` despues de investigarlos.
- Seguridad: toda salida de logging pasa por `SecretRedactionFilter` y oculta tokens incluidos en URLs de Telegram.
- Persistencia local: `data/bot-log-checkpoint.json` esta ignorado por Git.

## D-022 - Updates pendientes conservadas

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: ejecutar polling con `drop_pending_updates=False` explicito.
- Limite: solo se procesan updates que Telegram todavia conserve; las ya descartadas por Telegram no se pueden recuperar.

## D-023 - Runtime unico, estable y actualizable

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: `.python-version` fija el ultimo CPython estable exacto y Windows, CI y Docker deben coincidir hasta el patch; actualmente Python 3.14.6.
- Dependencias: `requirements.in` enumera paquetes directos sin prereleases y `requirements.txt` fija todo el grafo instalado; actualmente PTB 22.8, python-dotenv 1.2.2, gspread 6.2.1 y google-auth 2.55.2.
- Automatizacion: Quality valida entorno nativo y Docker; Runtime Update busca actualizaciones semanalmente y solo las fusiona despues de pasar ambas validaciones.
- Rollback: si una actualizacion falla durante validacion no modifica `main`; si aparece una regresion posterior, revertir el commit de runtime, recrear `.venv` desde el lock restaurado y volver a validar antes de pushear.
- Motivo: eliminar diferencias entre Windows y deploy sin renunciar a releases estables recientes.
