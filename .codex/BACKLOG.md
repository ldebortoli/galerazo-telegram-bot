# TODO

## P1

- Conectar el sistema de gastos con el Google Sheet real cuando el usuario proporcione o confirme el spreadsheet ID, worksheet y credenciales de service account.
- Garantizar una sola instancia del bot y una sola ventana del panel Galerazo; identificar la instancia que usa el token. Aplicar el mismo bloqueo de panel unico a Spider Tracker.
- Corregir `TELEGRAM_LOG_CHAT_ID` o los permisos del bot: Telegram responde `Chat not found` al enviar eventos de inicio.
- Implementar un checkpoint incremental de `data/bot.log` al terminar cada instruccion de Codex, revisar solo entradas nuevas y corregir errores detectados.
- Corregir `/debug` para responder con la update JSON o adjuntarla como archivo cuando exceda el limite de Telegram.
- Registrar junto con cada fallo la update JSON que lo causo para facilitar el debug posterior.

## P2

- Activar el deploy automatico de Railway solo cuando el usuario lo pida y despues de verificar `RAILWAY_TOKEN` y `RAILWAY_SERVICE_ID`.
- Ampliar la suite automatizada para base de datos, permisos, migraciones de chat, paginacion y panel de control.
- Hacer que la pestana seleccionada del panel Galerazo se vea mas grande que las no seleccionadas.
- Mostrar comandos como `/comando` en `/help` en vez de `- comando`.
- Agregar `/start` con saludo y referencia a `/help`.
- Verificar y garantizar que el polling procese updates pendientes recibidas mientras el bot estuvo apagado, salvo descarte de Telegram.
- Mostrar el icono del conejo en la barra de tareas mientras el panel Galerazo esta abierto.

# IN PROGRESS

No hay tareas en curso.

# DONE

- [2026-07-10] Agregar X a todas las pantallas de `/config`, con cierre permitido solo para admines/devs y pruebas de permisos.
- [2026-07-10] Renombrar el ranking a `Tabla de Galerazas` y mostrar nombre visible mas user ID sin menciones ni requests de Telegram.
- [2026-07-10] Corregir la doble respuesta de `/galerazas`, eliminar el fallback `unknown_command`, ignorar comandos inexistentes y agregar pruebas de regresion.
- [2026-07-10] Aplicar la memoria persistente a 14 proyectos activos y configurar `~/.codex/AGENTS.md` mas un inicializador idempotente para todos los proyectos futuros.
- [2026-07-10] Crear la memoria persistente `.codex/`, agregar el punto de entrada `AGENTS.md`, consolidar cambios pendientes y pushear `main`.
- [2026-07-10] Migrar el bot a `python-telegram-bot` manteniendo arquitectura modular y procesamiento secuencial.
- [2026-07-10] Implementar niveles common/admin/dev, blacklist global y restricciones por chat.
- [2026-07-10] Implementar tracking y migracion de grupos a supergrupos para todas las tablas con `chat_id`.
- [2026-07-10] Implementar logging, anuncios, reportes, backup, debug, estadisticas de chats y salida de grupos.
- [2026-07-10] Implementar La Galeraza, rankings y paginacion reutilizable persistida.
- [2026-07-10] Implementar configuracion por grupo, idiomas espanol/ingles y grupos configurables.
- [2026-07-10] Implementar triggers de texto/media para grupos y supergrupos.
- [2026-07-10] Implementar gastos local-first y adaptador opcional de Google Sheets.
- [2026-07-10] Implementar panel Windows para encender, apagar, reiniciar, configurar y ver logs.
- [2026-07-10] Agregar icono de conejo con galera al panel, ejecutable y acceso de CODEX APPS.
- [2026-07-10] Corregir inicio del panel, reporte de errores tempranos y deteccion nativa de procesos Windows.
- [2026-07-10] Garantizar commit/rollback y cierre explicito de cada conexion SQLite; validar migracion, backup y limpieza temporal en Windows.
