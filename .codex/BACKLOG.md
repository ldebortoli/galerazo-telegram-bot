# TODO

## P1

- Conectar el sistema de gastos con el Google Sheet real cuando el usuario proporcione o confirme el spreadsheet ID, worksheet y credenciales de service account.
- Corregir `TELEGRAM_LOG_CHAT_ID` o los permisos del bot: Telegram responde `Chat not found` al enviar eventos de inicio.

## P2

- Activar el deploy automatico de Railway solo cuando el usuario lo pida y despues de verificar `RAILWAY_TOKEN` y `RAILWAY_SERVICE_ID`.
- Ampliar la suite automatizada para base de datos, permisos, migraciones de chat, paginacion y panel de control.

# IN PROGRESS

No hay tareas en curso.

# DONE

- [2026-07-10] Agrandar la pestana seleccionada del panel y fijar identidad AppUserModelID/icono del conejo en Windows.
- [2026-07-10] Mostrar `/comando` en `/help`, agregar `/start` bilingue y fijar `drop_pending_updates=False`.
- [2026-07-10] Aplicar globalmente la ejecucion automatica de tareas de `USER_QUEUE.md` en los 14 proyectos activos y en el inicializador de proyectos futuros.
- [2026-07-10] Implementar el checkpoint incremental obligatorio de `data/bot.log`, corregir los errores detectados y redactar tokens en logs existentes y futuros.
- [2026-07-10] Corregir `/debug` con JSON en mensaje/archivo y adjuntar la update JSON a cada error no manejado.
- [2026-07-10] Garantizar una sola instancia local del bot por token y una sola ventana de los paneles Galerazo/Spider; cerrar Galerazo ante conflictos de polling externos con diagnostico explicito.
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
