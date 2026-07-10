# TODO

## P1

- Conectar el sistema de gastos con el Google Sheet real cuando el usuario proporcione o confirme el spreadsheet ID, worksheet y credenciales de service account.

## P2

- Activar el deploy automatico de Railway solo cuando el usuario lo pida y despues de verificar `RAILWAY_TOKEN` y `RAILWAY_SERVICE_ID`.
- Crear una suite automatizada formal para base de datos, permisos, migraciones de chat, paginacion y panel de control.

# IN PROGRESS

- [P0] Crear la memoria persistente `.codex/`, validar el estado consolidado del proyecto, committear y pushear todos los cambios pendientes.

# DONE

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
