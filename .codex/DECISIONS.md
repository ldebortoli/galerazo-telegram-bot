# Decisiones tecnicas

Este archivo es append-only a nivel conceptual: no borrar decisiones anteriores. Si una decision cambia, agregar una nueva entrada que indique cual reemplaza y por que.

## D-076 - Reinicio confirmado por reejecucion del proceso

- Estado: vigente.
- Fecha: 2026-07-29.
- Decision: `/reiniciarbot` guarda una confirmacion SQLite asociada a chat/mensaje/DEV solicitante. No hay tarea de expiracion activa: las confirmaciones vencidas se limpian solo al ejecutar ese comando o al tocar sus botones. Tras confirmar, el proceso espera que la cola PTB de updates se vacie, detiene el polling y se reejecuta con `os.execv`.
- Motivo: evita reinicios accidentales, conserva consistencia de las updates ya obtenidas y funciona de la misma forma en Windows y Docker sin reiniciar el contenedor.

## D-077 - Detener polling antes de drenar un reinicio confirmado

- Estado: vigente.
- Fecha: 2026-07-29.
- Decision: despues de una confirmacion de `/reiniciarbot`, esperar al callback actual, detener `Application.updater`, drenar `application.update_queue` y recien entonces llamar `stop_running` y reejecutar el proceso. Si PTB informa que el updater ya estaba detenido, continuar con el drenaje.
- Motivo: acota el reinicio bajo trafico continuo sin descartar updates. Las que lleguen despues de detener polling permanecen en Telegram y se recuperan al arrancar porque `drop_pending_updates=False`.

## D-078 - Anuncios sin previews de enlaces

- Estado: vigente.
- Fecha: 2026-07-29.
- Decision: los envios de broadcast, el canal de anuncios y las novedades usan `LinkPreviewOptions(is_disabled=True)` de python-telegram-bot.
- Motivo: evitar tarjetas externas no solicitadas y mantener los anuncios compactos, incluidos enlaces de Cafecito y changelogs.

## D-079 - Regresion contra mojibake en traducciones

- Estado: vigente.
- Fecha: 2026-07-29.
- Decision: las cadenas de `i18n.py` que requieran caracteres no ASCII pueden usar escapes Unicode; la suite rechaza los marcadores `Ã`, `Â` y U+FFFD en todas las traducciones runtime.
- Motivo: impedir que errores de recodificacion UTF-8 vuelvan a mostrarse a usuarios de Telegram.

## D-080 - Resumen de broadcast legible por linea

- Estado: vigente.
- Fecha: 2026-07-29.
- Decision: el resultado de `/anuncio` muestra encabezado y cada contador en lineas independientes, tanto en español como en inglés.
- Motivo: mejorar el escaneo del resultado en chats sin perder métricas de envio.

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

## D-024 - ICO multirresolucion nativo para el panel

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: generar `assets/galerazo-bot-icon.ico` desde el PNG fuente durante `build_control_panel.ps1`, con capas DIB nativas para 16, 20, 24, 32, 40, 48, 64, 128 y 256 pixeles.
- Motivo: GDI corrompia visualmente las capas pequenas comprimidas como PNG aunque el directorio ICO fuera valido; la barra de titulo de Tk necesita representaciones nativas compatibles.
- Validacion: extraccion correcta de la capa de 16 pixeles, lectura del `WM_GETICON` de la ventana activa y prueba estructural automatizada.

## D-025 - Estado explicito para cada tarea de USER_QUEUE

- Estado: vigente; refuerza D-019.
- Fecha: 2026-07-10.
- Decision: toda tarea incorporada desde `USER_QUEUE` debe figurar en `IN PROGRESS`, `DONE` o con `[BLOCKED: causa exacta]` en su propia linea del backlog; no puede quedar como pendiente P1/P2 sin calificacion.
- Cierre: antes de finalizar un run se auditan todas las entradas procesadas contra esos estados. Si se agota la cuota durante una tarea, queda en `IN PROGRESS` y el handoff registra el siguiente paso exacto.
- Alcance: regla global en `C:\Users\calei\.codex\AGENTS.md` y en el inicializador de proyectos futuros.

## D-026 - Ruleta rusa atomica y deshabilitada por defecto

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: `/ruletarusa` mantiene una recamara aleatoria y cantidad de disparos por `chat_id`/`user_id` en SQLite; cada jugada usa `BEGIN IMMEDIATE` y elimina el estado al acertar.
- Configuracion: pertenece al grupo `ruletarusa`, deshabilitado por defecto. Antes de consumir estado se valida que el bot sea admin con permiso para restringir miembros.
- Protecciones: common solo se apunta a si mismo; admin/dev puede apuntar al usuario respondido; bot, admines y devs no son expulsados.
- Migracion: `russian_roulette_states` forma parte obligatoria de `Database.migrate_chat_id`.

## D-027 - Sin dependencia adicional para comandos y listas

- Estado: vigente.
- Fecha: 2026-07-10.
- Decision: no agregar otra libreria para prefijos, listas, usuarios, media o ruleta. `python-telegram-bot`, SQLite y la libreria estandar ya cubren las APIs necesarias.
- Simplificacion aplicada: `user_display.py` concentra resolucion y formato `nombre (id)` para blacklist, restricciones y gastos; se eliminaron helpers duplicados y el helper de gastos obsoleto.
- Motivo: una dependencia nueva no reemplazaria logica significativa y aumentaria mantenimiento.

## D-028 - Fecha Telegram en timezone argentino para La Galeraza

- Estado: vigente; reemplaza la parte temporal de D-002/D-022 que dependia del momento de procesamiento.
- Fecha: 2026-07-11.
- Decision: la clave diaria se obtiene de `message.date`, se interpreta como timestamp Telegram y se convierte con `ZoneInfo("America/Argentina/Buenos_Aires")`; nunca se usa la hora de recepcion ni el timezone local de Windows.
- Dependencia: `tzdata` queda fijada para que la zona IANA exista de forma reproducible en Windows, Docker y CI.
- Candidatos: solo updates `message` originales de usuarios reales; bots, `edited_message`, posts de canal y `filters.StatusUpdate.ALL` quedan excluidos.
- Auditoria: `galeraza_daily_winners.message_date` conserva el timestamp Telegram del ganador.

## D-029 - Payload estructurado para triggers reproducibles

- Estado: vigente.
- Fecha: 2026-07-11.
- Decision: `triggers.payload_json` guarda datos estructurados para contactos, ubicaciones, lugares y encuestas; archivos y media siguen usando `file_id`.
- Tipos: texto, foto, animacion, video, audio, voz, documento, videomensaje, sticker, dado, contacto, ubicacion, lugar y encuesta.
- Limite: eventos de servicio y mensajes que dependen de configuracion externa no portable, como pagos o juegos ajenos, se rechazan.

## D-030 - El panel es propietario del proceso local

- Estado: vigente; reemplaza la parte de D-010 que permitia cerrar el panel sin apagar el bot.
- Fecha: 2026-07-11.
- Decision: `WM_DELETE_WINDOW` ejecuta `stop_bot` antes de destruir la UI. La misma politica se registro globalmente y se aplico al panel de Spider Tracker.
- Motivo: evitar procesos administrados sin una UI visible para controlarlos.

## D-031 - Orden por chat con paralelismo entre chats

- Estado: vigente; reemplaza D-002.
- Fecha: 2026-07-11.
- Decision: usar un `BaseUpdateProcessor` de PTB que serializa FIFO todas las updates del mismo chat, permite hasta 256 updates activas de chats distintos y une la secuencia del ID viejo/nuevo durante migraciones a supergrupo.
- Persistencia: la adjudicacion diaria ejecuta `BEGIN IMMEDIATE` y conserva la restriccion unica `(chat_id, game_date)` para que dos candidatos nunca sumen dos puntos.
- Rendimiento: el bloqueo solo dura el procesamiento de una update de ese chat; no bloquea llamadas de otros chats y la resolucion canonica del `chat_id` se cachea en memoria.
- Motivo: preservar el primer mensaje y el orden causal de callbacks/comandos sin convertir un chat lento en un bloqueo global del bot.

## D-032 - Capas ICO nativas con alfa completo

- Estado: vigente; refina D-024.
- Fecha: 2026-07-11.
- Decision: generar cada tamano del ICO como DIB BGRA de 32 bits, con alfa continuo y mascara AND que marca los pixeles totalmente transparentes.
- Motivo: `Bitmap.GetHicon()` reducia las capas a 4 bits y el icono pequeno podia renderizar el fondo transparente como un rectangulo negro.
- Validacion: la suite exige 32 bits, alfa 0..255 y esquinas transparentes en las nueve capas; la ventana activa devolvio por `WM_GETICON` un recurso 16x16 con alfa 0 en sus cuatro esquinas.

## D-033 - Composicion compacta para iconos pequenos

- Estado: vigente.
- Fecha: 2026-07-11.
- Decision: en capas de 16 a 64 px, recortar automaticamente el area superior cuadrada del arte para mostrar conejo, cara y ala de la galera sin deformacion; las capas de 128/256 px mantienen la ilustracion completa.
- Motivo: el arte completo es alto y angosto, por lo que solo ocupaba 10 de 16 pixeles de ancho en la barra de tareas.
- Validacion: la capa activa 16x16 ocupa 14x14 con un margen uniforme de un pixel; la suite exige al menos 75% de ocupacion horizontal y vertical en todas las capas pequenas.

## D-034 - CI proporcional al cambio

- Estado: vigente.
- Fecha: 2026-07-11.
- Decision: commits solo documentales (`.codex`, Markdown y `.gitignore`) no disparan Quality; cambios sustantivos ejecutan un unico job Linux y cancelan runs anteriores de la misma rama.
- Docker: se separa en `docker-quality.yml` y corre automaticamente solo al cambiar Dockerfile, runtime, lock de dependencias o el propio workflow; tambien admite ejecucion manual.
- Deploy: mientras permanezca desactivado solo admite `workflow_dispatch`, por lo que ya no crea un run omitido en cada push.
- Runtime update: conserva frecuencia semanal, pero no compila ni prueba cuando la resolucion produce exactamente las mismas versiones.
- Limites: Quality tiene timeout de 10 minutos, Docker 15 y Runtime Update 20.
- Motivo: en repositorios privados GitHub contabiliza cada job por separado y redondea su duracion al minuto siguiente; los dos jobs cortos anteriores consumian al menos dos minutos por push.

## D-035 - Altura reservada para el estado de integraciones

- Estado: vigente.
- Fecha: 2026-07-11.
- Decision: el panel abre en `760x720`, no permite menos de `680x700` y reduce el padding vertical de Configuracion a 16 px.
- Motivo: con el layout anterior el label de logging solicitaba 21 px pero Tk solo le asignaba 14, cortando el texto inferior.
- Validacion: una prueba nativa de Windows instancia Tk a la altura minima y exige que `winfo_height >= winfo_reqheight` para el label.

## D-036 - Runtime Update publica el commit validado directamente

- Estado: vigente; reemplaza la creacion/fusion de PR automatica de D-023.
- Fecha: 2026-07-13.
- Decision: cuando cambian versiones, el workflow semanal valida primero el entorno nativo y la imagen Docker, crea un commit y hace un push normal de `HEAD` a `main`.
- Seguridad: no usa force push; si `main` avanzo durante el job, el push se rechaza sin sobrescribir cambios. El token conserva solo `contents: write` y los pushes hechos con `GITHUB_TOKEN` no encadenan nuevas ejecuciones de Actions.
- Motivo: el repositorio no permite que GitHub Actions cree pull requests con su configuracion actual; el run `29249239004` habia validado correctamente pero fallo al intentar crear el PR.
- Versiones validadas: Python 3.14.6, `anyio` 4.14.2 y `google-auth` 2.56.0; una prueba impide reintroducir permisos/CLI de pull request o force push.

## D-037 - Eventos de servicio humanos compiten por La Galeraza

- Estado: vigente; reemplaza la exclusion de eventos de servicio establecida en D-028.
- Fecha: 2026-07-15.
- Decision: todo `Update.message` original de grupo o supergrupo con `effective_user` humano compite por el punto diario, incluidos mensajes de servicio como `new_chat_members`.
- Exclusiones: bots, `edited_message`, updates sin usuario, usuarios globalmente bloqueados y usuarios restringidos en ese chat siguen sin competir.
- Consistencia: se mantienen el timestamp de Telegram, el timezone `America/Argentina/Buenos_Aires`, el orden FIFO por chat y la adjudicacion atomica de un unico ganador.
- Validacion: la regresion construye un mensaje `new_chat_members`, comprueba que PTB conserva su usuario efectivo y exige que sea candidato.

## D-038 - Auditoria exhaustiva de StatusUpdate

- Estado: vigente; refuerza D-037.
- Fecha: 2026-07-15.
- Decision: mantener en tests un mapa explicito de todas las constantes de `filters.StatusUpdate` disponibles en la version bloqueada de PTB; actualmente son 46 categorias.
- Regresion: cada categoria debe ser reconocida por su filtro especifico, por `StatusUpdate.ALL`, conservar un `effective_user` humano y ser candidata. La igualdad exacta entre el mapa y la biblioteca obliga a auditar categorias nuevas al actualizar PTB.
- Ruta: otra prueba verifica que el `MessageHandler` de preprocesamiento recibe especificamente eventos de pin, miembros agregados y miembros que salen.

## D-039 - Moderacion multimedia sin costo

- Estado: vigente como restriccion; la seleccion final de servicios sigue pendiente.
- Fecha: 2026-07-20.
- Decision: la moderacion de triggers debe cubrir imagenes y videos sin generar cargos ni habilitar servicios pagos. Ninguna integracion puede contratarse, superar una capa gratuita o requerir consumo facturable sin una nueva autorizacion explicita del usuario.
- Alcance tecnico: OpenAI Moderation puede analizar gratis imagenes y fotogramas extraidos de videos, pero no recibe video directamente ni reemplaza un detector especializado de CSAM. PhotoDNA Cloud es gratuito para organizaciones aprobadas y actualmente se limita a imagenes.
- Politica pendiente: hasta disponer de cobertura especializada gratuita para cada tipo, se debe confirmar con el usuario si el bot rechaza de forma cerrada toda imagen o video no escaneable.

## D-040 - Triggers multimedia permanecen habilitados sin escaner

- Estado: vigente; resuelve la politica pendiente de D-039 mientras el bot opere en grupos confiables.
- Fecha: 2026-07-20.
- Decision: no bloquear, rechazar ni alterar triggers de imagen o video por falta de moderacion configurada. El comportamiento actual se conserva y la integracion de escaneres queda pospuesta.
- Motivo: el usuario confirmo que, por ahora, el bot participa en grupos confiables y no quiere perder funcionalidad multimedia.
- Riesgo aceptado: hasta retomar la integracion no existe deteccion automatica de pornografia o CSAM en esos triggers. Una futura moderacion debe seguir sin generar cargos y no puede activar un modo estricto sin una nueva indicacion del usuario.

## D-041 - Moderar imagenes solo al crear triggers

- Estado: vigente; refina D-040 para la primera integracion de moderacion.
- Fecha: 2026-07-20.
- Decision: cuando exista `OPENAI_API_KEY`, analizar la imagen una unica vez al ejecutar `/agregartrigger`, antes de persistir el trigger. No analizar triggers al reproducirlos ni reescanear los ya guardados.
- Motivo: prevenir que se incorporen nuevas imagenes sexuales sin agregar latencia a cada activacion del trigger.
- Activacion: usar una API key de proyecto restringida con acceso de escritura solo a `/v1/moderations`, guardada exclusivamente en `.env`. Sin clave, conservar el comportamiento actual y no bloquear imagenes.
- Limite: esta capa usa `omni-moderation-latest` para contenido sexual general; no se presenta como detector fiable de CSAM. Videos siguen fuera de esta primera etapa.

## D-042 - Moderacion multimedia en memoria al crear triggers

- Estado: vigente; reemplaza el limite de videos de D-041 y concreta D-039/D-040.
- Fecha: 2026-07-20.
- Decision: con `OPENAI_API_KEY`, moderar antes de persistir fotos, documentos de imagen y stickers como imagen; para videos, documentos de video y videomensajes, extraer exactamente cuatro frames interiores al 20%, 40%, 60% y 80% de la duracion y enviarlos juntos a `omni-moderation-latest`.
- Rendimiento: no moderar al reproducir triggers ni reescanear triggers existentes. PyAV y Pillow procesan bytes en memoria mediante `asyncio.to_thread`; otros chats pueden continuar y el chat del comando conserva su orden.
- Privacidad local: no crear archivos temporales ni guardar bytes, frames o respuestas en SQLite. Sobrescribir y vaciar buffers mutables en `finally`, y liberar las copias internas al cerrar sus objetos.
- Errores: sin clave, omitir el escaneo para conservar D-040. Con clave configurada, cualquier error de descarga, decodificacion o API rechaza solo ese intento de alta para no persistir media sin verificar.
- Credencial: guardar una clave de proyecto restringida con escritura solo para `/v1/moderations` en `.env`; el panel la muestra como campo secreto. No versionarla ni registrarla.
- Limite: se bloquea la categoria sexual disponible para imagenes. Esta integracion no se presenta como detector especializado ni garantia de deteccion de CSAM.

## D-043 - Setup e instalador local componibles para Windows

- Estado: vigente.
- Fecha: 2026-07-20.
- Decision: usar `scripts/setup.ps1` como orquestador idempotente de la instalacion local y `instaladores/Instalar Galerazo Bot.cmd` como puente de doble clic, siguiendo el patron de Dankiebot sin duplicar codigo ni artefactos del proyecto.
- Composicion: el setup reutiliza `scripts/sync_windows_runtime.ps1` y `build_control_panel.ps1`; crea `.env` solo cuando falta, prepara directorios locales, valida el runtime, compila la UI, crea accesos en `CODEX APPS` y Escritorio y abre el panel salvo `-NoLaunch`.
- Entorno: una `.venv` con el Python exacto se conserva y actualiza desde el lock; se recrea solo si falta, usa otra version o se pide `-ForceRecreate`. Antes de cualquier borrado se verifica que sea una carpeta real dentro del repositorio y no un reparse point.
- Distribucion: el instalador no crea un paquete autonomo, no copia el repositorio, no instala Docker y nunca incorpora o reemplaza secretos. Las actualizaciones siguen siendo Git mas una nueva ejecucion del setup.

## D-044 - Deploy GCE con imagenes reproducibles y publicacion manual

- Estado: vigente; reemplaza a Railway como recomendacion principal sin activar ni borrar su workflow historico.
- Fecha: 2026-07-20.
- Decision: ejecutar produccion en una VM GCE `e2-micro` mediante Docker Compose, con imagen `linux/amd64` inmutable en Artifact Registry y acceso administrativo por IAP/SSH.
- Construccion: el camino por defecto prueba, construye y publica desde la PC para consumir cero minutos de Actions. GitHub puede construir el mismo target solo mediante `workflow_dispatch`; nunca publica por cada push.
- Seguridad: imagen runtime minima y no root, filesystem de solo lectura, capabilities eliminadas, sin puertos, secretos en `/etc/galerazo`, SQLite/backups en bind mounts y autenticacion CI por Workload Identity Federation sin claves JSON persistentes.
- Deploy: una accion local confirmada copia scripts por IAP, crea un backup SQLite consistente, descarga antes de recrear, espera el healthcheck y restaura automaticamente la imagen anterior ante fallo. Las etiquetas usan commit/tag inmutable, no `latest`.
- Motivo: conservar costo bajo y control humano, evitar drift de runtime y hacer rollback sin reconstruir dentro de una VM de 1 GB.

## D-045 - Proyecto GCP compartido para la flota personal

- Estado: vigente; reemplaza la recomendacion de un proyecto exclusivo por bot en la guia de deploy.
- Fecha: 2026-07-20.
- Decision: usar `bot-fleet-production` como proyecto GCP generico para los bots personales y aislar cada bot mediante nombres de recursos, service accounts, contenedores, directorios, secretos y bases separados.
- Excepcion: crear proyectos distintos cuando cambien el cliente, el responsable de pago o los permisos y riesgos necesiten aislamiento fuerte.
- Motivo: centralizar presupuesto, operacion y dashboard sin multiplicar proyectos; crear proyectos adicionales no multiplica el Free Tier asociado a la cuenta de facturacion.

## D-046 - Guardarrail mensual de costos GCP

- Estado: vigente.
- Fecha: 2026-07-20.
- Decision: mantener el presupuesto `Bot Fleet - Monthly Guardrail` en USD 1 mensual sobre la cuenta de facturacion, actualmente vinculada solo a `bot-fleet-production`.
- Calculo: incluir Free Tier y los demas ahorros, pero excluir creditos promocionales, para advertir el costo que persistiria despues de la prueba gratuita.
- Alertas: gasto real al 10%, 50% y 100%, pronostico al 100%, con correo a administradores y usuarios de facturacion.
- Limite: el presupuesto no es un hard cap; Pub/Sub, Monitoring y cualquier apagado automatico permanecen sin configurar hasta una etapa posterior.

## D-047 - Herramientas locales de deploy en Windows

- Estado: vigente.
- Fecha: 2026-07-20.
- Decision: usar Docker Desktop instalado por usuario con backend WSL 2 y contenedores Linux/amd64, junto con Google Cloud CLI autenticado mediante la cuenta humana local.
- Proyecto predeterminado: `bot-fleet-production`.
- Motivo: evitar privilegios administrativos permanentes, construir localmente la misma arquitectura que produccion y reutilizar la autenticacion segura de `gcloud` sin claves JSON locales.

## D-048 - Artifact Registry compartido para la flota

- Estado: vigente.
- Fecha: 2026-07-20.
- Decision: usar el repositorio Docker `bots` en `us-central1` dentro de `bot-fleet-production`; separar las imagenes por nombre de bot y tags inmutables, por ejemplo `bots/galerazobot:COMMIT`.
- APIs habilitadas: Compute Engine, Artifact Registry, IAP e IAM Service Account Credentials.
- Motivo: compartir la infraestructura base y el almacenamiento gratuito disponible sin mezclar identidades, contenedores, datos ni secretos de bots distintos.

## D-049 - Fundacion GCP idempotente y permisos por repositorio

- Estado: vigente.
- Fecha: 2026-07-20.
- Decision: usar `scripts/deploy/Initialize-GcpBot.ps1` para asegurar las APIs y el registro compartidos, crear la service account especifica de cada bot y configurar acceso de runtime/publicacion solo sobre el repositorio `bots`.
- Permisos: `galerazo-vm` recibe `roles/artifactregistry.reader`; la cuenta local activa recibe `roles/artifactregistry.writer`. Ninguno de esos bindings se concede a nivel proyecto.
- Credenciales: la automatizacion usa la sesion humana de `gcloud`, no crea claves JSON y falla si detecta claves administradas por el usuario en la identidad de runtime.
- Repeticion: proyecto, facturacion, presupuesto, APIs y registro son infraestructura compartida; identidad, VM, secretos y datos son por bot. El script se puede ejecutar nuevamente sin duplicar recursos o bindings y nunca crea VM.

## D-050 - VPC dedicada dual-stack y VM sin IPv4 publica

- Estado: vigente.
- Fecha: 2026-07-20.
- Decision: ejecutar `galerazo-prod` como `e2-micro` no Spot en `us-central1-a`, Debian 12 y disco `pd-standard` de 30 GB, conectado a la VPC custom `bot-fleet` y subred `bots-us-central1` dual-stack con IPv6 externo efimero y Private Google Access.
- Entrada: ninguna regla publica general. La unica regla de `bot-fleet` permite tcp/22 desde `35.235.240.0/20` solo a instancias con tag `iap-ssh`; la administracion usa IAP y OS Login.
- Salida: no usar IPv4 externa, IP reservada, Cloud Router ni Cloud NAT mientras Telegram, repositorios y Artifact Registry sean accesibles por IPv6/Private Google Access. Cualquier fallback que pueda cobrar requiere una nueva decision.
- Protecciones: Shielded Secure Boot, vTPM, integrity monitoring y deletion protection activados; la service account es `galerazo-vm` con scope `cloud-platform` y permisos IAM minimos a nivel recurso.

## D-051 - Runbook por etapas con pausas manuales de seguridad

- Estado: vigente.
- Fecha: 2026-07-20.
- Decision: `Invoke-GceBotLifecycle.ps1` es el orquestador canonico para reproducir Foundation, Infrastructure, Prepare, Publish, Deploy, Release y Rollback sin duplicar la logica de los scripts especializados.
- Manual inevitable: alta/prueba/facturacion y login de Google; eleccion del proyecto/presupuesto; ingreso del token y secretos; seleccion de un backup SQLite consistente. Los secretos nunca se pasan por argumentos.
- Guardas: la infraestructura exige aceptar el posible costo; Release/Deploy/Rollback exigen confirmacion de produccion; el deploy rechaza `latest`, un bot local activo y la ausencia de `bot.env` o base remotos.
- Reutilizacion: en la misma cuenta/proyecto se repiten solo los recursos por bot. En otra cuenta se repite el bloque manual de cuenta/proyecto y luego el mismo orquestador. Bot Control Center podra invocar `Release` sin reimplementar el deploy.

## D-052 - Verificacion automatica y liviana del host GCE

- Estado: vigente.
- Fecha: 2026-07-20.
- Decision: `Initialize-GceHost.ps1` copia y ejecuta `deploy/gce/verify-host.sh` despues del bootstrap para validar Docker/Compose/Cloud CLI, servicio, owners y modos sin imprimir valores de secretos.
- Estado pristino: el flag manual `--expect-pristine` exige placeholder, cero imagenes/contenedores y ausencia de base/Compose antes de cargar los datos del primer deploy; la verificacion normal sigue siendo idempotente despues de configurar produccion.
- Observabilidad: no instalar Ops Agent por defecto en la `e2-micro`; usar las metricas nativas de CPU, red y disco y consultar RAM por IAP cuando sea necesario, evitando carga permanente adicional en una VM de 1 GB.

## D-053 - Transferencia de secretos por archivo privado e IAP

- Estado: vigente; refina la pausa manual de D-051: el usuario completa `.env` y confirma la operacion, pero no pega secretos en SSH ni los pasa por argumentos.
- Fecha: 2026-07-20.
- Decision: agregar `Set-GceBotSecrets.ps1` y la accion `Configure` para aceptar solo las variables de `.env.example`, forzar el path SQLite del contenedor y transferir un archivo temporal por IAP a un directorio remoto modo 0700.
- Instalacion: `install-config.sh` valida sin imprimir valores, conserva `bot.env.previous`, instala como root 0600 y ejecuta `verify-host.sh --expect-configured`; ante error restaura la configuracion anterior. Los temporales local/remoto siempre se eliminan.
- Integraciones opcionales: si existe un JSON valido en `GOOGLE_SHEETS_CREDENTIALS_JSON_PATH`, se copia como secreto remoto y el path se adapta al contenedor; valores vacios de OpenAI o Sheets permanecen omitidos.

## D-054 - Migracion SQLite consistente, privada y reversible

- Estado: vigente.
- Fecha: 2026-07-20.
- Decision: agregar `Migrate-GceBotDatabase.ps1` y la accion `MigrateData`; exigir confirmacion y que el bot local y todos los contenedores remotos esten apagados antes de reemplazar produccion.
- Consistencia: crear la copia local mediante `sqlite3.Connection.backup`, ejecutar `PRAGMA integrity_check` antes y despues de transferir y no copiar archivos `-wal`/`-shm`.
- Instalacion: transferir por IAP a un directorio 0700, instalar como 10001:10001/0600 y conservar una copia consistente de la base remota anterior en `/srv/galerazo/backups`; ante fallo restaurarla y limpiar temporales.

## D-055 - Contrato de credenciales remotas para Bot Control Center

- Estado: vigente como contrato; la pantalla aun no esta implementada en el proyecto separado Bot Control Center.
- Fecha: 2026-07-20.
- Decision: Bot Control Center reutilizara la accion `Configure` y su transporte IAP en vez de leer/escribir secretos por un protocolo propio.
- UI y seguridad: mostrar solo estado presente/ausente, recibir reemplazos en campos enmascarados, pedir confirmacion y auditar la accion. Nunca recuperar valores secretos remotos ni acoplar su modificacion al boton normal de deploy.

## D-056 - Inspector booleano y parche parcial de secretos

- Estado: vigente; implementa y refina D-055.
- Fecha: 2026-07-20.
- Decision: `Get-GceBotSecretStatus.ps1` copia por IAP un inspector root que devuelve exclusivamente booleanos. `Patch-GceBotSecrets.ps1` acepta un parche JSON local de hasta 32 KiB, lo transfiere por un directorio remoto 0700 y ejecuta una allowlist cerrada que preserva campos omitidos, impide borrar el token principal y soporta el JSON opcional de Sheets.
- Seguridad: los valores no se pasan por argumentos ni aparecen en salida; temporales locales/remotos se eliminan, la configuracion anterior se conserva para rollback y `verify-host.sh --expect-configured` valida el resultado. La operacion no reinicia ni despliega el bot.

## D-057 - Smoke test obligatorio de la imagen runtime

- Estado: vigente.
- Fecha: 2026-07-21.
- Decision: la imagen minima de produccion debe copiar `.python-version` junto al codigo y ejecutar `ensure_python_version()` dentro del target runtime antes de considerarse publicable.
- Aplicacion: el build/publicador local, Docker Quality y el workflow manual de Artifact Registry validan el target runtime real; el workflow manual carga, prueba y solo entonces publica exactamente esa imagen.
- Motivo: las pruebas del target `test` no detectaron que el primer runtime publicado omitía `.python-version`, lo que provocó un bucle de reinicios antes de iniciar Telegram.

## D-058 - Fallo seguro sin imagen anterior

- Estado: vigente.
- Fecha: 2026-07-21.
- Decision: si un deploy falla y existe una imagen anterior saludable, restaurarla; si es el primer deploy y no existe una imagen anterior, detener explícitamente el contenedor fallido.
- Motivo: evitar que `restart: unless-stopped` mantenga un bucle de reinicios y distinguir claramente en la salida si hubo rollback o sólo contención del fallo.

## D-059 - Red de host para salida IPv6 del contenedor

- Estado: vigente.
- Fecha: 2026-07-22.
- Decision: ejecutar Galerazobot con `network_mode: host` en `galerazo-prod` para reutilizar la salida IPv6 de la VM.
- Motivo: la VM no tiene IPv4 publica ni Cloud NAT; el bridge Docker sólo entregaba IPv4 al contenedor y `getMe` contra Telegram terminaba por timeout. La misma imagen con red de host resolvió IPv6 y obtuvo HTTP 200 de `api.telegram.org`.
- Seguridad: el bot no escucha puertos, Compose no publica ninguno, las capacidades siguen eliminadas, el filesystem permanece read-only y el firewall de GCE conserva únicamente la entrada administrativa por IAP.

## D-060 - Contrato efímero y enumerado para Bot Control Center

- Estado: vigente.
- Fecha: 2026-07-22.
- Decisión: `Invoke-GceBotctl.ps1` copia temporalmente por IAP un `deploy/gce/botctl.py` versionado, ejecuta sólo `status`, `triggers`, `media`, `moderate` o `stop` con argumentos validados y elimina el temporal. Las lecturas usan el SQLite real en modo lectura y Telegram bajo demanda; nunca devuelven el token. La moderación vuelve a resolver trigger, autor y chat antes de escribir y comunica resultados parciales. `stop` equivale únicamente a `docker compose stop bot`, sin `down` ni eliminación de base, imagen, secretos o configuración.
- Motivo: dar visibilidad y una contención segura ante bucles de reinicio sin instalar un daemon, abrir puertos administrativos ni aceptar comandos remotos libres.

## D-061 - Backup SQLite mensual compartido para la flota

- Estado: vigente.
- Fecha: 2026-07-22.
- Decisión: crear un bucket privado regional compartido por proyecto y aislar cada bot bajo `bots/<bot-id>/`; cada VM genera una copia consistente con `sqlite3.Connection.backup`, valida `PRAGMA integrity_check`, adjunta SHA-256 y la sube una vez por mes mediante un timer systemd persistente.
- Retención: conservar copias locales y remotas 400 días. Cloud Storage usa acceso uniforme, prevención de acceso público, soft delete de siete días y nombres inmutables; la identidad de runtime recibe sólo `roles/storage.objectCreator` sobre el bucket.
- Reutilización: `Enable-GceSqliteBackups.ps1` parametriza proyecto, VM, service account, bot, rutas y UID; el mismo bucket sirve a futuros bots sin copiar bases entre prefijos. La restauración permanece manual y confirmada mediante el flujo existente de `MigrateData`.
- Límite de aislamiento: el prefijo por bot es una separación lógica, no IAM, porque `storage.objectCreator` se concede sobre el bucket compartido. Se acepta para bots personales bajo el mismo dueño; clientes o dominios no confiables deben usar bucket o proyecto separado.
- Motivo: separar el backup de la VM sin introducir snapshots completos ni frecuencia/costo innecesarios mientras los datos no sean críticos.

## D-062 - Reporte diario de gasto mediante Cloud Billing exportado a BigQuery

- Estado: vigente.
- Fecha: 2026-07-22.
- Decision: usar `JobQueue.run_daily` de `python-telegram-bot` a una hora `America/Argentina/Buenos_Aires` configurable, con default 09:00, para consultar la exportacion estandar de Cloud Billing a BigQuery y enviar el resultado a `TELEGRAM_LOG_CHAT_ID`.
- Calculo: filtrar el `invoice.month` vigente y mostrar costo bruto, creditos y neto (`cost + credits`) por moneda, junto con la ultima hora de exportacion. La latencia de Billing se informa y este reporte no reemplaza el presupuesto ni sus alertas.
- Costos y seguridad: SQL parametrizado, tabla validada, cache y `maximum_bytes_billed=100 MiB`; sin canal o configuracion completa no se agenda ni consulta. GCE usa ADC de `galerazo-vm`, sin claves JSON, con `roles/bigquery.jobUser` en el proyecto y `roles/bigquery.dataViewer` solo en el dataset.
- Activacion: crear el dataset exige `-AcknowledgeBillableResource`; vincular la cuenta a la exportacion estandar es un paso manual de consola y la carga inicial puede demorar hasta cinco dias.

## D-063 - Cobertura local y CI con umbrales explicitos

- Estado: vigente.
- Fecha: 2026-07-22.
- Decision: medir `galerazo_bot` con `coverage.py` y branch coverage; exigir al menos 62% de sentencias y 36% de ramas mediante `scripts/check_coverage.py`.
- CI: `Quality` ejecuta la suite rapida una sola vez bajo cobertura. Docker sigue condicionado a cambios de runtime/contenedor y los workflows costosos permanecen manuales para proteger la cuota de Actions.
- Alcance: excluir `galerazo_bot/control_panel.py` de la metrica multiplataforma porque su layout Tk solo puede ejecutarse en Windows; mantener sus pruebas nativas y contratos estaticos fuera de ese porcentaje.
- Limite: coverage.py no expone una metrica separada de funciones; se documentan y controlan las metricas que el stack soporta.

## D-064 - Cobertura obligatoria del nucleo al 100%

- Estado: vigente desde 2026-07-22; reemplaza los umbrales numericos de D-063.
- La validacion local y `Quality` exigen 100% de sentencias y 100% de ramas para todo el nucleo multiplataforma incluido por `.coveragerc`; cualquier regresion falla.
- `galerazo_bot/control_panel.py` permanece fuera de esa metrica multiplataforma porque su layout Tk depende del runtime grafico nativo de Windows. El panel conserva su prueba de layout en Windows y contratos estaticos en la suite comun; esta exclusion debe seguir siendo explicita.
- Las pruebas agregadas para sostener el porcentaje deben validar comportamiento, errores y guardas reales. No se permiten ramas artificiales de produccion ni aserciones vacias para inflar la metrica.

## D-065 - Documentos de debug en memoria con timeout y reintento acotados

- Estado: vigente desde 2026-07-22.
- Los updates de debug que no entran en un mensaje se serializan a `BytesIO`; no se crean archivos temporales ni se depende de escritura local en el contenedor.
- La subida del documento usa 30 segundos para los timeouts HTTP de PTB y reintenta una sola vez exclusivamente ante `telegram.error.TimedOut`.
- Otros errores de Telegram, o un segundo timeout, conservan la respuesta localizada de fallo y se registran sin exponer el contenido del update.

## D-066 - Errores transitorios de polling no son errores no handleados

- Estado: vigente desde 2026-07-22.
- `python-telegram-bot` reintenta indefinidamente los `NetworkError` producidos por `getUpdates` y entrega esos fallos al error handler con `update=None`, sin job ni coroutine.
- Ese caso se registra localmente como warning resumido y no se envia al canal de logging, porque ya esta siendo manejado por el retry loop de PTB.
- Un `NetworkError` asociado a un update, job o coroutine sigue el flujo normal de error no handleado. `Conflict` mantiene su tratamiento separado y detiene la instancia para evitar dos pollers con el mismo token.

## D-067 - Releases de produccion agrupados y bajo pedido explicito

- Estado: vigente desde 2026-07-22.
- Las correcciones y funcionalidades ordinarias se implementan, validan, commitean y pushean, pero no publican una imagen en Artifact Registry ni despliegan GCE.
- Un reporte de bug de produccion no autoriza por si mismo un release. Publicar o desplegar requiere que el usuario lo pida explicitamente en la instruccion actual con expresiones como "hacer un release" o "desplegar".
- Docker local se usa solo cuando la superficie modificada necesita esa validacion; no implica release. Cuando el usuario autoriza un release, se agrupan todas las correcciones acumuladas y se conserva el flujo completo de backup, healthcheck y rollback.

## D-068 - Timeouts HTTP centrales para solicitudes Telegram

- Estado: vigente desde 2026-07-26.
- Las solicitudes normales de `python-telegram-bot` usan timeouts de conexion, lectura, escritura y pool de 30 segundos configurados en `ApplicationBuilder`; el valor predeterminado de cinco segundos era insuficiente para envios transitorios como `/triggers`.
- Un `TimedOut` al crear una respuesta paginada se registra localmente como warning y no se reintenta: Telegram puede haber aceptado el envio aunque la respuesta se haya perdido, por lo que reintentar podria duplicar el mensaje.

## D-069 - Menus de BotFather limitados a comandos publicos

- Estado: vigente desde 2026-07-26.
- Al iniciar, el bot sincroniza los comandos sugeridos mediante los scopes `all_private_chats` y `all_group_chats`, con descripciones en espanol por defecto e ingles para `language_code=en`.
- Solo se incluyen comandos de nivel `COMMON`; privados reciben los generales y grupos agregan Galeraza y triggers habilitados por defecto. Se excluyen siempre los comandos de admin/dev y los grupos configurables deshabilitados por defecto (`gastos`, `ruletarusa`). El scope global se elimina para no conservar sugerencias anteriores sensibles ni aplicarlas a canales.

## D-070 - Versionado y anuncios de release

- Estado: vigente desde 2026-07-26.
- `CURRENT_VERSION` y su entrada `## [version]` en `CHANGELOG.md` definen la release. Antes de cada deploy solicitado por el usuario, el agente incrementa la version y agrega los cambios importantes; los fixes menores se resumen como "Correcciones y mejoras" salvo indicacion contraria del usuario.
- SQLite conserva solamente la ultima version anunciada en `release_state`. Durante el inicio, el bot envia las notas de la version al canal de anuncios y solo actualiza ese estado tras un envio exitoso, por lo que los reinicios no duplican novedades ni un fallo las pierde.
- `/version` es publico y devuelve `CURRENT_VERSION`. El changelog inicial es `0.1` y se anunciara cuando esa version se despliegue por primera vez.

## D-071 - Menus BotFather diferenciados para administradores

- Estado: vigente desde 2026-07-26; reemplaza el alcance de usuarios comunes de D-069 para grupos.
- Los grupos reciben el menu de comandos comunes, excepto gastos. El scope `all_chat_administrators` agrega los comandos de nivel `ADMIN` solamente a los administradores del grupo.
- Los comandos de nivel `DEV` y todos los comandos de gastos permanecen ocultos en BotFather. La ruleta rusa vuelve a aparecer como comando comun de grupos, aunque cada grupo puede mantenerla deshabilitada por configuracion.

## D-072 - Changelog y version obligatorios por cambio funcional

- Estado: vigente desde 2026-07-26; amplifica D-070.
- Todo cambio funcional actualiza `CHANGELOG.md` en el mismo commit. El agente elige el incremento de version salvo numero indicado expresamente por el usuario: capacidades visibles importantes incrementan la version menor y varios fixes menores se agrupan bajo una sola linea "Correcciones y mejoras".
- Al agregar, eliminar, renombrar, cambiar permisos o descripciones de un comando, el mismo trabajo debe actualizar definiciones/pruebas de BotFather y ejecutar la sincronizacion directa. Los cambios sin impacto de comandos no requieren esa llamada externa.
- La version actual pasa a `0.2`, que agrupa `/version`, los anuncios de release y menus BotFather por rol. Se anunciara en el proximo deploy solicitado.

## D-073 - Gastos exclusivos de desarrollo

- Estado: vigente desde 2026-07-26; reemplaza los permisos previos de la familia de gastos.
- Los seis comandos de gastos (`/habilitargastos`, `/deshabilitargastos`, `/gasto`, `/ultimosgastos`, `/estadogastos` y `/sincronizargastos`) requieren `UserLevel.DEV`.
- Motivo: los gastos se consolidan en una planilla global y el usuario solicito que solamente el desarrollador pueda habilitarlos, cargarlos, consultarlos y sincronizarlos.
- La configuracion por chat y la persistencia local se conservan: el grupo sigue deshabilitado inicialmente y un desarrollador debe habilitarlo antes de registrar un gasto.

## D-074 - Gastos globales de desarrollo sin configuracion por chat

- Estado: vigente desde 2026-07-26; reemplaza la configuracion por chat de D-073.
- Se eliminan `/habilitargastos` y `/deshabilitargastos`, la opcion Gastos de `/config` y la condicion `configurable_group` de los cuatro comandos restantes.
- `/gasto`, `/ultimosgastos`, `/estadogastos` y `/sincronizargastos` requieren `DEV` y pueden usarse en cualquier tipo de chat. La base conserva el `chat_id` de cada gasto como dato de registro, no como permiso.
- Los callbacks de tableros antiguos de Gastos se detectan antes de controles de nivel y eliminan el mensaje para retirar la UI obsoleta en el primer toque.

## D-075 - Broadcast de anuncios con opt-out por chat

- Estado: vigente desde 2026-07-27.
- `/anuncio` exige `DEV`, recorre solo chats activos y envia de forma secuencial. Cada envio usa el idioma del chat y agrega un pie que apunta a `/config`; se valida el limite para espanol e ingles antes de enviar el primer mensaje.
- `chat_settings.announcements_enabled` tiene default activo, migra con el `chat_id` y puede modificarse por `/config` en privados y por administradores en grupos/supergrupos. El canal de anuncios recibe siempre la copia central.
- `Forbidden` y `BadRequest` que identifican expulsion/bloqueo/chat inexistente marcan el chat inactivo. Timeouts y otros errores transitorios se contabilizan sin degradar la estadistica de `/chats`.
- Las notas de `CHANGELOG.md` al iniciar una version nueva reutilizan el broadcast; la version se considera anunciada solo cuando pudo enviarse al canal central.
## D-081 - Novedades de version en texto plano (2026-07-29)

`CHANGELOG.md` conserva Markdown para lectura en el repositorio, pero `current_release_notes()` elimina los delimitadores de codigo en linea antes de entregar texto a Telegram. Los broadcasts no dependen de `parse_mode`, asi se evitan comillas literales y no se introducen problemas de escape Markdown.

## D-082 - Pie compacto de anuncios (2026-07-29)

Los anuncios mantienen una separacion visual antes de la donacion y dejan el aviso de configuracion en la linea inmediatamente siguiente. Se aplica en todos los idiomas y a los changelogs distribuidos porque comparten `format_announcement()`.

## D-083 - Enlace fijo al canal en anuncios (2026-07-29)

Todo broadcast incluye el enlace publico de anuncios antes de la donacion. La URL permanece identica y la etiqueta se localiza para espanol e ingles; se conserva la misma composicion para anuncios manuales y changelogs de release.

## D-084 - PID renovado despues de reinicio local (2026-07-29)

El panel inicia el bot con `GALERAZO_PANEL_MANAGED=1`. El bot reescribe `data/bot.pid` al comenzar solo bajo esa marca, por lo que un relanzamiento Windows posterior a `/reiniciarbot` actualiza el PID que el panel consulta. Las ejecuciones manuales no crean ni reclaman ese estado del panel.

## D-085 - Relevo atomico del PID local (2026-07-29)

El reinicio Windows puede coexistir transitoriamente con el proceso padre y su hijo. Antes del relevo se crea `data/bot.restart`; el panel conserva el estado `REINICIANDO` hasta 15 segundos y no borra el PID previo durante esa ventana. El nuevo proceso reemplaza `bot.pid` atomically y borra la marca. Una marca vencida se descarta para no bloquear un encendido real.

## D-086 - Fallos de novedades visibles en logging (2026-07-29)

El runtime Docker incluye `CHANGELOG.md`, porque las notas de release son un artefacto necesario al iniciar. Si aun asi no puede leerse, `_announce_current_release()` registra el error y lo reenvia al canal de logging, ya que Telegram y la configuracion de logging estan disponibles en ese punto. Un fallo del propio canal no impide que el bot inicie.

## D-087 - Drenaje acotado y migraciones SQLite versionadas (2026-07-29)

`/reiniciarbot` y `/apagar` comparten una confirmacion persistida de cinco minutos y una unica ruta de apagado: primero detienen el `Updater`, luego esperan como maximo 60 segundos por las updates ya aceptadas. Si un handler no termina, se registra el timeout en el canal de logging y se fuerza el reinicio o apagado para evitar que un bucle infinito deje al proceso en estado indeterminado. Docker concede 65 segundos al `SIGTERM` de un deploy, por lo que el cierre normal de PTB deja de recibir updates y drena antes de que Docker lo fuerce.

Los cambios de esquema se implementan como migraciones inmutables y registradas en `schema_migrations`, ejecutadas al iniciar sobre la SQLite persistente remota. El deploy conserva el volumen y crea un backup consistente antes de sustituir la imagen; `MigrateData` sigue reservado exclusivamente para reemplazar la base remota por una copia local confirmada.

## D-088 - Changelog publico orientado a usuarios (2026-07-29)

Las entradas de `CHANGELOG.md` y las novedades que el bot distribuye solo comunican cambios visibles en comandos publicos. Los comandos exclusivos DEV, infraestructura, Docker, SQLite, migraciones, despliegues y correcciones internas no se incluyen. La trazabilidad tecnica se conserva en commits, documentacion tecnica y la memoria persistente del proyecto.

## D-089 - Resumen de broadcast automatico en logging (2026-07-29)

Un broadcast de release no tiene un usuario invocador al cual responder. Cuando consigue enviar al canal de anuncios, el bot manda al canal de logging el mismo resumen de contadores que devuelve `/anuncio`. El resumen es observabilidad operativa y no condiciona que la version se marque como anunciada.
