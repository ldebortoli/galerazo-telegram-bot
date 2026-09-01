# Changelog

## [0.56] - 2026-09-01

- Correcciones y mejoras del release: la configuración opcional vacía vuelve a usar valores seguros y cada imagen se valida de forma aislada antes de reemplazar el contenedor activo.
- Bot Control Center puede avisar en el canal de logs cuándo comienza y cómo termina un release programado.

## [0.55] - 2026-08-31

- `/debug` ahora está disponible para cualquier usuario y aparece entre los comandos generales; devuelve únicamente el update que Telegram entregó para ese mensaje.

## [0.54] - 2026-08-28

- Nuevo Hisopo Usado: aparece camuflado, revela su arte con cera al capturarlo, resta 2 puntos y ocupa un 5 % tomado íntegramente del Hisopo Común. También se incorpora a la colección, las reglas y la Mini App.

## [0.53] - 2026-08-28

- Correcciones y mejoras del registro de errores: el canal muestra solo la excepción y recibe el traceback junto con la update completa en un TXT adjunto; los callbacks que Telegram ya considera vencidos se descartan silenciosamente.

## [0.52] - 2026-08-28

- Se suman seis Hisopos especiales a la tienda y al álbum unificado: Mini, Pico, Pala, Gota, Rosáceo y Alfiler. Pueden comprarse repetidamente o regalarse mediante una compra como los demás coleccionables.

## [0.49] - 2026-08-28

- `/donar` presenta una invitación más breve para aportar con Telegram Stars, sumarse al Club del Hisopo o donar la jubilación de la abuela; se retiran las aclaraciones adicionales y el acceso externo queda identificado simplemente como `Cafecito`.

## [0.48] - 2026-08-28

- Cada donación, compra, regalo o cuota del Club confirmada mediante Telegram Stars ahora genera un aviso en el canal de logging con la persona, el concepto, el destinatario cuando corresponde y el importe. Las reentregas del mismo cobro no duplican el aviso y Cafecito queda fuera porque no envía esos eventos al bot.

## [0.47] - 2026-08-28

- Nuevo Hisopo Galerazo, una edición especial de galera, conejo y oro en honor al Galerazo y a su creador. Se incorpora a la tienda por 6000 Stars, apenas por encima de Dengue, y puede comprarse más de una vez o regalarse como los demás Hisopos especiales.

## [0.46] - 2026-08-28

- Correcciones y mejoras: el Club del Hisopo queda como una membresía mensual de apoyo y ya no acredita Estelares, Hisopos, puntos ni ventajas; los Estelares obtenidos anteriormente se conservan. La Mini App aclara este alcance, corrige `Invitale` y simplifica la opción para aparecer con nombre o de forma anónima en el Top colaboradores.

## [0.45] - 2026-08-28

- La tienda permite comprar más de una unidad del mismo Hisopo o regalarlo a otra persona mediante su `@alias` conocido por el bot o su `user_id`; el destinatario queda firmado en la factura y recibe la unidad tras el pago confirmado.
- La Mini App reúne los Hisopos encontrados y especiales en una sola colección, elimina la sección separada y suma la vista `Todos los grupos` con los totales acumulados de cada tipo y de capturas históricas.

## [0.44] - 2026-08-28

- Los catorce Hisopos cosméticos ahora también pueden recibirse como regalo: aparecen en la colección global del destinatario sin generar una compra, una donación ni un período del Club.

## [0.43] - 2026-08-28

- Nueva tienda de Hisopos cosméticos con trece coleccionables permanentes en Telegram Stars: de Caca, Sereno, Carmesí, Colosal, Masivo, Bacteriófago, Mundial, Invisible, Isótopo, Infinito, Cuásar, Big Bang y Dengue. Son globales y no dan puntos ni modifican probabilidades; Dengue es la pieza máxima a 5000 Stars.
- `/donar` incorpora aportes de 25, 100 y 500 Stars y el Club del Hisopo renovable cada 30 días por 100 Stars, con un Hisopo Estelar por cada período confirmado. Los pagos y reembolsos son idempotentes y retiran el beneficio correspondiente al devolverse.
- Nuevos `/donantes`, `/paysupport` y `/terminos`: el ranking cuenta únicamente donaciones confirmadas, descuenta reembolsos y mantiene anónimo el nombre salvo autorización expresa.
- Nueva Mini App móvil con álbumes por grupo, colección cosmética, tienda, Club y aportes. Valida la firma y antigüedad de `initData`; desde un grupo abre el álbum propio de ese chat y desde el privado permite elegir solo entre grupos con colección conocida.
- Se incorpora `aiohttp==3.14.3`, se actualizan el lock reproducible y la imagen Docker, y se agregan catorce artes originales para los cosméticos y el Club.

## [0.42] - 2026-08-27

- Correcciones y mejoras: cuando un Hisopo se vence, tanto la leyenda como el aviso emergente indican de forma breve cuál era su tipo y que se perdió por haber vencido, sin agregar detalles de puntos ni de colección.

## [0.41] - 2026-08-21

- Correcciones y mejoras: Frenético y Agujero negro ya no publican ni refrescan la mejor marca de la carrera. Cada participante mantiene su contador individual hasta 20 y ve su propio progreso solamente en la notificación privada de cada pulsación; el mensaje se edita al revelar un Misterioso y al mostrar el desenlace.

## [0.40] - 2026-08-21

- Correcciones y mejoras: `/reglashisopo` ahora presenta una versión resumida y más legible, organizada en bloques con títulos, negritas, comandos monoespaciados y mayor separación visual mediante HTML seguro de Telegram. Conserva probabilidades, premios, vencimientos y excepciones esenciales en los 18 idiomas.

## [0.39] - 2026-08-21

- Correcciones y mejoras: `/reglashisopo` ahora dice correctamente que una aparición no capturada se vence, no que se pudre. La terminología se alineó en los 18 idiomas sin cambiar la rareza Putrefacto.

## [0.38] - 2026-08-21

- Correcciones y mejoras: `/coleccionhisopos` ya no agrega al final la explicación extensa sobre Misterioso, Gigante, carreras y vencimientos; esa información queda centralizada en `/reglashisopo`.

## [0.37] - 2026-08-21

- Correcciones y mejoras: el premio individual del Hisopo Milagroso mantiene un mínimo de 15 puntos y la mitad redondeada hacia arriba del puntaje líder, pero ahora queda limitado a un máximo de 1000 puntos para evitar su crecimiento exponencial indefinido.
- El parche seguro de configuración remota ignora correctamente entradas vacías de la lista de variables a eliminar.

## [0.36] - 2026-08-21

- Nuevos Hisopos Frenético y Agujero negro, ambos con 4 % de aparición y carreras persistentes/atómicas a 20 pulsaciones. El Frenético entrega 3 puntos; el Agujero negro entrega 10 si se juega en soledad o transfiere hasta 10 puntos desde los rivales según sus pulsaciones.
- Nuevo coleccionable Vencido: el primer toque tardío revela el tipo, no altera puntajes y cambia la foto; las apariciones no Misteriosas entregan Vencido, mientras que un Misterioso solo revela su tipo real.
- La colección pasa a 16 categorías, las pulsaciones y sus callbacks sobreviven migraciones de grupo, y se agregan tres artes y variables de `file_id` independientes para Frenético, Agujero negro y Vencido.

## [0.35] - 2026-08-21

- Nuevo Hisopo bomba (4 %): tablero persistente de 16 casillas con una desactivación por +10 puntos, una explosión por -10 y catorce intentos neutros. Los clics se resuelven atómicamente, sobreviven migraciones y cambian la foto al desenlace.
- La colección incorpora el Bomba como decimotercer tipo, muestra `hisopo gigante` sin el calificativo cooperativo y, si un Misterioso ocultaba un Bomba o un Gigante, entrega el Misterioso solamente a quien revela el tipo real.
- Se agregaron los tres artes del Bomba y variables separadas para la aparición, la desactivación y la explosión.

## [0.34] - 2026-08-21

- La colección ahora incluye Misterioso: cada captura nueva suma uno al Misterioso y uno al tipo revelado. Si contenía un Fugaz vencido, suma solamente el Misterioso. Los tipos no descubiertos se muestran con `❓` en vez de un cuadro blanco.
- El ranking conserva y muestra con cero puntos a quien obtiene un Falso como primera captura.

## [0.33] - 2026-08-21

- Correcciones y mejoras: al revelar un Hisopo falso, el mensaje ahora cuenta que la captura resultó ser falsa y aclara que no suma ningún punto.

## [0.32] - 2026-08-21

- Correcciones y mejoras: todos los envíos a Telegram ahora respetan preventivamente los límites generales y por chat. Si Telegram responde con control de frecuencia, el bot espera el plazo indicado y realiza hasta tres intentos totales también para fotos, multimedia, ediciones, borrados y demás operaciones.

## [0.31] - 2026-08-21

- Correcciones y mejoras: los reportes de excepciones ahora muestran el tipo y el detalle del error al comienzo, antes del contexto y del traceback completo.

## [0.30] - 2026-08-21

- Antes de publicar un nuevo Hisopo, el bot intenta eliminar en ese grupo las apariciones con más de 24 horas. Los fallos se registran y nunca impiden enviar la aparición nueva.

## [0.29] - 2026-08-20

- Nuevo comando `/coleccionhisopos`: muestra la colección histórica por usuario y grupo, con cantidades y progreso sobre los 11 tipos reales. Recupera capturas anteriores, combina datos al migrar a supergrupo y no usa temporadas.
- Los fallos al enviar la foto de una aparición de Hisopo ahora llegan al manejador y al canal de errores con el contexto de la aparición; las agendas fallidas quedan cerradas como fallidas.

## [0.28] - 2026-08-20

- Cada grupo ahora puede acumular como máximo 10 apariciones de Hisopos con horario aleatorio para una misma fecha del día siguiente. Al llenar el cupo, las capturas conservan sus puntos y efectos; las apariciones activadas por mensajes y la aparición inmediata del Gemelo no consumen ese límite.
- Los envíos de mensajes que Telegram frena temporalmente por control de frecuencia ahora respetan la espera indicada y reintentan hasta el mismo máximo de tres intentos, en vez de terminar como error no manejado.

## [0.27] - 2026-08-20

- Las reglas del Hisopo gigante ahora aclaran cómo se calcula su objetivo: el total de miembros informado por Telegram menos Galerazo, con un máximo de 15, incluyendo otros bots que formen parte de chats pequeños.

## [0.26] - 2026-08-20

- El Hisopo milagroso ahora entrega el mayor valor entre 15 puntos y la mitad, redondeada hacia arriba, del puntaje del líder del grupo al momento de capturarlo.

## [0.25] - 2026-08-20

- El Recolector suma el Hisopo gigante cooperativo: pide hasta 15 ayudas únicas, muestra el progreso y entrega 4 puntos a cada participante solo si el grupo lo completa dentro de 20 minutos.
- Nuevo Hisopo milagroso ultrarraro, con un premio especial calculado al capturarlo.
- Las probabilidades incorporan al gigante con 0,25 % y al milagroso con 0,10 %, mientras el común queda en 46,65 %.

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

## [0.2] - 2026-07-26

- Comando `/version` para consultar la version actual del bot.
- Anuncio automatico de novedades al canal de anuncios una sola vez por version desplegada.
- Menus de BotFather diferenciados para usuarios comunes y administradores de grupos.

## [0.1] - 2026-07-26

- Galeraza diaria sincronizada por chat con tabla de puntajes y paginacion.
- Triggers configurables con soporte de texto y multimedia.
- Permisos por nivel, configuracion por grupo, bloqueo y restricciones por chat.
- Reportes, anuncios, backups SQLite, panel local de control y diagnostico.
- Moderacion opcional de media al crear triggers.
