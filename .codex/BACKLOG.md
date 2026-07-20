# TODO

## P1

- [BLOCKED: falta que el usuario cree una API key de proyecto restringida a `/v1/moderations` y la guarde como `OPENAI_API_KEY` en `.env`; la variable no esta configurada y no se debe pedir ni exponer la clave en el chat] Implementar moderacion gratuita solo al ejecutar `/agregartrigger` sobre una imagen: descargarla temporalmente desde Telegram, consultar `omni-moderation-latest`, rechazar contenido sexual marcado y no volver a escanear al reproducir el trigger.
- [BLOCKED: falta que el usuario confirme spreadsheet ID, worksheet y credenciales de service account] Conectar el sistema de gastos con el Google Sheet real.
- [BLOCKED: el token `gh` no tiene scope `user`/Plan y el navegador disponible no tiene sesion GitHub; requiere iniciar sesion o autorizar explicitamente ampliar el scope] Confirmar visualmente si la cuenta personal tiene medio de pago cargado. La documentacion oficial confirma que, si no existe un medio valido, Actions se bloquea al agotar la cuota y no cobra excedentes.

## P2

- [BLOCKED: el usuario priorizo primero imagenes; no existe una alternativa especializada gratuita confirmada para video y no se deben bloquear ni alterar los triggers actuales] Extender en el futuro la moderacion gratuita a videos de triggers.
- [BLOCKED: requiere pedido explicito del usuario y luego verificar RAILWAY_TOKEN y RAILWAY_SERVICE_ID] Activar el deploy automatico de Railway.

# IN PROGRESS

No hay tareas en curso.

# DONE

- [2026-07-20] Definir la arquitectura conceptual de un dashboard general para bots remotos. Recomendacion: crear una aplicacion separada y local-first, con registro de hosts/bots, adaptadores de transporte por proveedor (IAP/SSH para Google, SSH para VPS y API donde corresponda) y una interfaz comun de solo lectura para estado, logs, triggers y consultas SQLite seguras. Cada bot conserva su proceso, secretos, base y logs aislados; el dashboard no expone puertos publicos ni abre el archivo SQLite por red. Reinicio, deploy y escrituras se reservan para una fase posterior con permisos, confirmaciones y auditoria.
- [2026-07-19] Aclarar acceso remoto a una VM Google y visualizacion local de SQLite/triggers. La VM puede administrarse por SSH mediante IAP sin IPv4 publica ni IP fija; la configuracion recomendada es IPv6 externa gratuita para la salida del bot, IAP restringido al puerto 22 y un dashboard de solo lectura ejecutado en la VM sobre localhost, visible desde la PC mediante port forwarding SSH. SQLite no debe montarse ni exponerse directamente por red; para datos en vivo conviene una API/dashboard remoto y para analisis local una copia consistente. El panel Tk actual solo controla procesos locales y requeriria una extension especifica para administrar la VM.
- [2026-07-19] Aclarar la recomendacion de hosting, los limites de gasto y la capacidad multi-bot. Recomendacion final: Railway Hobby con hard limit de USD 5 si se priorizan simplicidad, corte de gasto nativo y varios servicios; Google Compute Engine Free si USD 0 es prioritario y se acepta configurar un proyecto exclusivo, una sola `e2-micro` elegible, `pd-standard` de hasta 30 GB, IPv6 sin IPv4, cuotas, alertas y apagado automatizado no instantaneo. Una `e2-micro` cobra por tipo/horas, no por porcentaje de CPU/RAM, y puede alojar prudentemente 3-5 bots Python livianos similares con procesos, entornos y SQLite separados; Railway Free queda razonablemente limitado a uno por el credito mensual de USD 1 y un solo volumen persistente.
- [2026-07-19] Investigar hosting 24/7 gratuito o de bajo costo para Galerazo Bot. El bot necesita proceso siempre activo y disco persistente, pero no dominio/IP publica; la base real ocupa 172032 bytes, todos los datos locales 856990 bytes y una sonda de importacion uso 54,2 MiB. Resultado: Google Compute Engine `e2-micro` es la opcion estable de costo cero con IPv6; Railway Hobby (USD 5/mes) es la mas simple por la preparacion existente; Fly.io ronda USD 2,17/mes con 256 MB y 1 GB persistente; DigitalOcean parte de USD 4/mes mas USD 0,80 por backup semanal; un mini PC domestico conviene solo con hardware ya disponible o a varios anos y requiere contemplar electricidad, cortes, Internet y UPS. No se activo ningun deploy.
- [2026-07-15] Auditar las 46 categorias de `filters.StatusUpdate` y validar explicitamente que pin, altas y bajas llegan al preprocesador y compiten con autor humano; 64 pruebas locales y Quality OK.
- [2026-07-15] Hacer que todo mensaje original de grupo/supergrupo con un usuario humano, incluidos eventos de servicio como `new_chat_members`, compita por La Galeraza; validar 61 pruebas y reiniciar el bot.
- [2026-07-13] Reparar el workflow semanal fallido `29249239004`, actualizar `anyio` 4.14.1 -> 4.14.2 y `google-auth` 2.55.2 -> 2.56.0, y validar 61 pruebas en Windows, Quality y Docker Quality.
- [2026-07-11] Corregir el texto truncado del estado de logging: ampliar el panel, ajustar padding y agregar una prueba Tk nativa que confirma 21/21 px de altura asignada.
- [2026-07-11] Reducir GitHub Actions a un job Linux por cambio sustantivo, cero runs para commits documentales, Docker solo por cambios de runtime/contenedor y deploy manual mientras siga desactivado.
- [2026-07-11] Agrandar el icono de barra de tareas con una composicion compacta no deformada para capas de 16 a 64 px; pasar de 10x14 a 14x14 visibles en la capa activa de 16 px.
- [2026-07-11] Corregir el fondo negro del icono pequeno: regenerar las nueve capas ICO como DIB BGRA de 32 bits con alfa/mascara AND, recompilar el lanzador y verificar la ventana activa.
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
