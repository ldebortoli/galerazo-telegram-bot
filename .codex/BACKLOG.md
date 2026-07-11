# TODO

## P1

- [BLOCKED: falta que el usuario confirme spreadsheet ID, worksheet y credenciales de service account] Conectar el sistema de gastos con el Google Sheet real.

## P2

- [BLOCKED: requiere pedido explicito del usuario y luego verificar RAILWAY_TOKEN y RAILWAY_SERVICE_ID] Activar el deploy automatico de Railway.

# IN PROGRESS

No hay tareas en curso.

# DONE

- [2026-07-11] Reemplazar la serializacion global por orden FIFO por chat usando `PerChatUpdateProcessor`, mantener paralelismo entre chats, coordinar migraciones a supergrupo y reforzar La Galeraza con una transaccion SQLite inmediata.
- [2026-07-11] Corregir con backup previo el ganador historico de Dankgentina del 2026-07-11: [Lewito] Leonardo (360780605), mensaje 1337843, reemplazo a Luke Inverse sin dejar el punto duplicado.
- [2026-07-11] Corregir La Galeraza para usar `message.date` de Telegram convertido con `tzdata` a `America/Argentina/Buenos_Aires`, ignorando bots, ediciones y eventos de servicio.
- [2026-07-11] Hacer que cerrar los paneles Galerazo y Spider Tracker apague sus procesos administrados y establecer la regla global para proyectos futuros.
- [2026-07-11] Extender triggers con animaciones, contactos, ubicaciones, lugares y encuestas, ademas de los tipos multimedia existentes; rechazar eventos no reproducibles y validar todo en una suite de 54 pruebas.
- [2026-07-11] En `/debug`, enviar archivos largos sin caption y nombrarlos `Debug de la update {update_id}`.
- [2026-07-11] Agregar `/lil` con respuesta `LIL`.
- [2026-07-11] Exponer y validar `/eliminartrigger` y `/eltrigger` como aliases de borrado en `/help`.
- [2026-07-11] Mostrar `/ruletarusa`, aliases y comandos configurables apagados en `/help`, manteniendo el filtro por nivel.
- [2026-07-10] Impedir bloquear al propio bot y responder `Ni se te ocurra...`.
- [2026-07-10] Hacer que `/debug` envie JSON puro sin fences Markdown.
- [2026-07-10] Unificar listas de usuarios con nombre sin `@`, ID y alias `/bloqueados`, conservando paginacion.
- [2026-07-10] Agrupar `/help` por familias y filtrar comandos segun nivel/configuracion.
- [2026-07-10] Corregir tildes y adaptar los textos visibles en espanol a voseo argentino, con prueba de regresion.
- [2026-07-10] Extender triggers con aliases de borrado, nombres con espacios de 5 a 32 caracteres, stickers y dados animados.
- [2026-07-10] Aceptar `.`, `>`, `$`, `galerazobot` y `galerazo_bot` como prefijos de comandos.
- [2026-07-10] Implementar `/ruletarusa` persistente, configurable, deshabilitada por defecto, migrable y con protecciones de bot/admin/dev.
- [2026-07-10] Ampliar la suite a 44 pruebas para base, permisos, migraciones con colisiones, paginacion, panel, triggers y ruleta.
- [2026-07-10] Revisar librerias y simplificar el formato/resolucion comun de usuarios sin agregar dependencias innecesarias.
- [2026-07-10] Corregir el icono pequeno de la barra de titulo con un ICO multirresolucion nativo y verificar el recurso asignado a la ventana activa.
- [2026-07-10] Corregir el icono nativo del panel Galerazo y el acceso directo; mostrar alerta de canal de logging inaccesible en Configuracion.
- [2026-07-10] Unificar Windows, Docker y CI en Python 3.14.6, actualizar y fijar todas las librerias, automatizar upgrades validados y documentar rollback.
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
