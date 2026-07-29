# Changelog

## [0.7] - 2026-07-29

- Nuevo comando exclusivo de desarrollo `/apagar`, con la misma confirmacion privada y expiracion de cinco minutos que `/reiniciarbot`.
- Correcciones y mejoras: reinicios y apagados dejan de aceptar polling, drenan las updates ya aceptadas y fuerzan el cierre tras 60 segundos si un handler queda bloqueado.
- Correcciones y mejoras: los deploys Docker dan 65 segundos de cierre ordenado antes de forzar el contenedor, conservando las updates que Telegram mantiene pendientes.
- Correcciones y mejoras: SQLite aplica migraciones versionadas sobre la base remota existente. Cada deploy crea un backup previo; la primera migracion elimina la tabla legacy ya reemplazada de botoneras de Galeraza.

## [0.6] - 2026-07-29

- Nuevo comando publico `/donar` y texto de Cafecito incluido en todos los anuncios distribuidos a chats.
- Nuevo comando exclusivo de desarrollo `/reiniciarbot`, con confirmacion privada, expiracion de cinco minutos y reinicio ordenado despues de procesar las updates ya recibidas.
- Correcciones y mejoras: al confirmar un reinicio, el polling se detiene antes de drenar las updates aceptadas, evitando que trafico continuo posponga el reinicio indefinidamente.
- Correcciones y mejoras: los anuncios y broadcasts deshabilitan las previews de enlaces de Telegram.
- Correcciones y mejoras: el panel local conserva el estado correcto del bot despues de `/reiniciarbot` en Windows.
- Correcciones y mejoras: el runtime Docker incluye `CHANGELOG.md` y los fallos al leer novedades se reportan tambien al canal de logs.
- Correcciones y mejoras: el panel muestra el estado de reinicio y evita perder el PID nuevo durante el relevo de procesos en Windows.
- Correcciones y mejoras: todos los anuncios incluyen el enlace al canal de anuncios antes de la donacion, con etiqueta localizada.
- Correcciones y mejoras: los anuncios dejan el aviso de `/config` inmediatamente debajo del texto de donacion.
- Correcciones y mejoras: las novedades distribuidas eliminan los delimitadores Markdown de comandos y valores para no mostrarlos como comillas literales en Telegram.
- Correcciones y mejoras: se corrigieron textos con codificacion UTF-8 dañada y se agrego una prueba global para impedir mojibake en traducciones.
- Correcciones y mejoras: el resumen de `/anuncio` ahora muestra cada resultado en su propia línea.

## [0.5] - 2026-07-27

- Nuevo comando de desarrollo `/anuncio` para enviar anuncios a todos los chats activos y al canal de anuncios.
- Cada chat puede habilitar o deshabilitar anuncios desde `/config`; la preferencia empieza habilitada e incluye chats privados y canales.
- Las novedades de versiones desplegadas ahora se distribuyen con el mismo sistema de anuncios y actualizan chats eliminados, bloqueados o expulsados al detectarlos.

## [0.4] - 2026-07-26

- Gastos deja de ser configurable por grupo: sus cuatro comandos son exclusivos de desarrollo y funcionan en cualquier tipo de chat.
- Los tableros de configuracion antiguos de Gastos se eliminan al interactuar con ellos.

## [0.3] - 2026-07-26

- El registro, consulta, activacion y sincronizacion de gastos ahora esta restringido exclusivamente a desarrolladores.

## [0.2] - 2026-07-26

- Comando `/version` para consultar la version actual del bot.
- Anuncio automatico de novedades al canal de anuncios una sola vez por version desplegada.
- Menus de BotFather diferenciados para usuarios comunes y administradores de grupos.

## [0.1] - 2026-07-26

- Galeraza diaria sincronizada por chat con tabla de puntajes y paginacion.
- Triggers configurables con soporte de texto y multimedia.
- Permisos por nivel, configuracion por grupo, bloqueo y restricciones por chat.
- Reportes, anuncios, backups SQLite, panel local de control y diagnostico.
- Registro opcional de gastos con Google Sheets y moderacion opcional de media al crear triggers.
