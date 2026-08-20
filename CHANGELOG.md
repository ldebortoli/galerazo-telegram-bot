# Changelog

## [0.24] - 2026-08-20

- Nuevo comando `/reglashisopo` con las reglas completas, probabilidades, vencimientos y efectos del Recolector de Hisopos en los 18 idiomas del bot.

## [0.23] - 2026-08-20

- El Hisopo misterioso conserva sus 20 minutos aunque contenga un fugaz, pero el premio fugaz vence al minuto: después se revela sin sumar puntos ni programar otra aparición.

## [0.22] - 2026-08-20

- Los Hisopos falso y putrefacto ahora aparecen disfrazados de común, plateado, dorado o diamante y revelan su identidad al capturarlos.
- El Hisopo radiactivo cambia de valor durante sus 20 minutos: permanece negativo durante la primera mitad y aumenta hasta 6 puntos cerca del vencimiento, mostrando el resultado recién al capturarlo.

## [0.21] - 2026-08-20

- El Hisopo falso ahora se disfraza de común hasta la captura, y el misterioso contiene y revela uno de los otros tipos respetando sus probabilidades relativas.
- El Hisopo gemelo lanza una nueva aparición inmediatamente al capturarlo y conserva una sola aparición programada para el día siguiente.
- El tipo real, la apariencia inicial y los valores aleatorios quedan persistidos y migran correctamente entre grupos y supergrupos.

## [0.20] - 2026-08-20

- Ajustamos las probabilidades del Recolector: el Hisopo diamante ahora es el más raro, mientras que el gemelo, falso, radiactivo y putrefacto aparecen con mayor frecuencia.

## [0.19] - 2026-08-20

- El Recolector suma siete Hisopos especiales: diamante, fugaz, misterioso, putrefacto, radiactivo, falso y gemelo, con premios, penalizaciones y comportamientos propios.
- La Tabla de Hisopos ahora admite puntajes negativos.

## [0.18] - 2026-08-20

- El Recolector de Hisopos ahora viene habilitado por defecto en grupos y supergrupos. Los chats que lo hayan desactivado desde `/config` conservan su eleccion.

## [0.17] - 2026-08-20

- Nuevo juego configurable `Recolector de Hisopos` para grupos y supergrupos, con apariciones aleatorias en cinco intensidades, hisopos comunes, plateados y dorados, captura por botonera y tabla `/hisopos`.
- Los hisopos vencen a los 20 minutos y cada captura programa una aparicion persistente para un horario aleatorio del dia siguiente.
- El juego, sus mensajes y su configuracion estan disponibles en los 18 idiomas del bot y todos sus datos migran al convertir un grupo en supergrupo.

## [0.16] - 2026-08-17

- Correcciones y mejoras: los envios de texto con una demora transitoria de Telegram realizan hasta tres intentos para priorizar la entrega, aunque el aviso pueda repetirse. La Galeraza conserva el punto ganado y registra el resultado si los tres intentos fallan.

## [0.15] - 2026-08-09

- `/config` incorpora Runa Simi, usando Quechua sureño para todos los textos del bot.

## [0.14] - 2026-08-09

- Correcciones y mejoras: los textos en guaraní ya no muestran el prefijo incorrecto `rehegua` al comienzo de cada mensaje.

## [0.13] - 2026-08-08

- Correcciones y mejoras: el selector de idioma de `/config` agrupa cuatro opciones por fila para ocupar menos espacio.

## [0.12] - 2026-08-08

- Los anuncios y novedades ahora incluyen el enlace al repositorio oficial del bot.

## [0.11] - 2026-08-08

- Correcciones y mejoras: el selector de idioma de `/config` agrupa opciones en filas compactas y los empates de `/galerazas` usan un guion alineado para distinguir las posiciones compartidas.

## [0.10] - 2026-08-08

- `/config` incorpora Español de España, ruso, latín, japonés, italiano, francés, alemán, holandés, chino simplificado y tradicional, portugués de Brasil y Portugal, catalán, vasco y guaraní para todos los textos del bot. Los nombres de comandos se mantienen iguales en todos los idiomas.

## [0.9] - 2026-08-08

- Correcciones y mejoras: todos los comandos ahora requieren un prefijo de ejecucion, para que los mensajes comunes no activen acciones del bot accidentalmente.

## [0.8] - 2026-08-01

- La tabla de `/galerazas` ahora muestra posiciones compartidas ante empates y mantiene alineados los usuarios que comparten puesto, incluso al pasar entre paginas.
- `/galerazas` informa cuando todavia no hay puntajes en el chat.

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
