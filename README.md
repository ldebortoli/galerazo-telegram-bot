# Galerazo Bot

Base para un bot de Telegram con una version estable y reproducible de Python, `python-telegram-bot` y SQLite.

## Comandos

- `help` / `ayuda`: muestra los comandos disponibles para tu nivel de usuario.
- `start`: saluda y muestra como abrir la ayuda.
- `hola`: responde un saludo.
- `lil`: responde `LIL`.
- `nivel`: muestra el nivel detectado para el usuario.
- `bloquear`: bloquea un usuario. Solo devs.
- `desbloquear` / `desloquear`: desbloquea un usuario. Solo devs.
- `listanegra` / `bloqueados`: muestra los usuarios bloqueados. Solo devs.
- `novedad`: envia una noticia al canal de anuncios. Solo devs.
- `reportar`: envia un reporte de bug al canal de logging. Maximo 1 por usuario por dia.
- `habilitargastos`: habilita el sistema de gastos en el chat actual. Solo admines del chat, quien agrego el bot o devs.
- `deshabilitargastos`: deshabilita el sistema de gastos en el chat actual. Solo admines del chat, quien agrego el bot o devs.
- `gasto`: registra un gasto en el chat actual si el sistema de gastos esta habilitado.
- `ultimosgastos`: lista los ultimos gastos del chat actual.
- `estadogastos`: muestra el estado de gastos y de Google Sheets. Solo admines del chat, quien agrego el bot o devs.
- `sincronizargastos`: intenta sincronizar gastos pendientes con Google Sheets. Solo admines del chat, quien agrego el bot o devs.
- `restringir`: restringe un usuario en el grupo actual. Solo admines del chat, quien agrego el bot o devs.
- `habilitar`: vuelve a habilitar un usuario restringido en el grupo actual. Solo admines del chat, quien agrego el bot o devs.
- `restringidos`: lista usuarios restringidos en el grupo actual. Solo admines del chat, quien agrego el bot o devs.
- `backup`: responde con un backup de SQLite. Solo devs.
- `debug`: responde con el objeto update del mensaje. Solo devs.
- `chats`: muestra estadisticas de chats por estado y tipo.
- `config`: abre el tablero de configuracion del grupo. Solo admines del chat, quien agrego el bot o devs.
- `galerazas`: muestra el ranking de La Galeraza en grupos/supergrupos.
- `hisopos`: muestra la tabla del Recolector de Hisopos en grupos/supergrupos, si el juego está habilitado.
- `coleccionhisopos`: muestra la colección histórica propia; al responder a otra persona, muestra la de ese usuario.
- `reglashisopo`: muestra las reglas completas del Recolector de Hisopos, incluso si el juego está deshabilitado.
- `agregartrigger` / `agrtrigger`: agrega un trigger respondiendo a un mensaje en grupos/supergrupos.
- `borrartrigger` / `eliminartrigger` / `eltrigger`: borra un trigger por nombre en grupos/supergrupos.
- `triggers`: lista los triggers del grupo o supergrupo.
- `ruletarusa`: juega a la ruleta rusa en el grupo o supergrupo, si el conjunto está habilitado.
- `salir`: hace que el bot salga de un grupo o supergrupo. Solo devs.

Todo comando requiere un prefijo de ejecucion: `/`, `!`, `.`, `>` o `$`. Por ejemplo: `/help`, `!help` o `.hola`. Un texto comun como `hola` o `galerazas` no ejecuta comandos.

Los comandos que no existen se ignoran silenciosamente. Cada comando implementado se procesa una sola vez y no cae en un handler generico posterior.

## Límites y reintentos de Telegram

Todas las llamadas salientes pasan por el limitador global de `python-telegram-bot`. El bot regula preventivamente el tráfico total y el dirigido a cada grupo o canal. Si Telegram responde con `429 Retry After`, pausa los envíos, espera el plazo exacto indicado más el margen de seguridad de la biblioteca y realiza como máximo dos reintentos: tres intentos totales. Esto se aplica a textos, fotos, multimedia, ediciones, borrados, respuestas de callbacks y demás métodos del Bot API; `getUpdates` queda excluido por diseño de la biblioteca.

Los reintentos por `TimedOut` permanecen separados y limitados a `send_message`: se espera 1 y 2 segundos entre tres intentos totales, aceptando el riesgo de duplicados cuando Telegram recibió el mensaje pero no confirmó la respuesta. Un `429` es un rechazo explícito y lo gestiona solamente el limitador global, evitando multiplicar accidentalmente ambos presupuestos.

## Estructura de comandos

Los handlers reales de Telegram se registran en `galerazo_bot/telegram_bot.py` con `CommandHandler`, `PrefixHandler`, `MessageHandler`, `CallbackQueryHandler` y `ChatMemberHandler`.

El dispatcher de comandos esta en `galerazo_bot/commands.py`. Ese archivo normaliza el texto, valida permisos y ejecuta el handler de dominio registrado.

Los comandos especificos estan en `galerazo_bot/command_handlers/`. Cada archivo contiene el handler y sus metodos auxiliares. Para agregar un comando nuevo:

1. Crear un archivo nuevo en `galerazo_bot/command_handlers/`.
2. Definir un diccionario `COMMANDS` con los nombres/aliases que activa ese archivo.
3. Importar ese `COMMANDS` en `galerazo_bot/command_handlers/__init__.py` y sumarlo al diccionario central.

El handler de dominio de `/hola` esta en `galerazo_bot/command_handlers/hola.py`. `galerazo_bot/handler_registration.py` concentra el registro nativo de `CommandHandler`, `PrefixHandler`, `CallbackQueryHandler` y `ChatMemberHandler`; `galerazo_bot/command_handlers/galerazas.py` contiene tanto el comando como los adaptadores de Telegram propios de la Galeraza.

Los comandos que pertenecen a un conjunto configurable usan `configurable_group` en su definicion. Si ese conjunto esta deshabilitado para un chat, el bot ignora esos comandos para todos los usuarios, incluidos devs.

## Instalacion

### Instalador local de Windows

La opcion recomendada para una PC nueva es hacer doble clic en:

```text
instaladores\Instalar Galerazo Bot.cmd
```

El instalador prepara la version exacta de Python, crea o reutiliza `.venv`, instala todas las dependencias bloqueadas, ejecuta las pruebas, crea `.env` si falta, compila la UI y sus iconos, instala accesos directos en `CODEX APPS` y el Escritorio, y finalmente abre el panel para probarlo localmente. Si `.env` ya existe, nunca lo reemplaza.

El mismo flujo se puede iniciar desde PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
```

Usa `-NoLaunch` para no abrir el panel, `-SkipTests` para omitir temporalmente la suite o `-ForceRecreate` para reconstruir `.venv`. El instalador es un puente hacia los scripts del repositorio: no copia el bot a otra ubicacion, no instala Docker y no incluye credenciales.

### Preparacion manual del runtime

```powershell
powershell -ExecutionPolicy Bypass -File scripts/sync_windows_runtime.ps1
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

`.python-version` es la fuente de verdad. El entorno local, GitHub Actions y Docker deben usar exactamente ese patch de Python. El bot y el panel rechazan el arranque si se ejecutan con otra version.

### Panel de control para Windows

Ejecuta `pythonw control_panel.py` para abrir una interfaz de escritorio desde la que se puede:

- encender, apagar y reiniciar el bot local;
- editar la configuracion de `.env`;
- cargar y ocultar la clave restringida usada para moderar media nueva;
- consultar el estado del proceso;
- ver el log local guardado en `data/bot.log`.

El panel guarda el PID en `data/bot.pid`. Cerrar la ventana apaga primero el árbol de procesos del bot y después cierra el panel. El acceso directo `Galerazo Bot` se puede colocar dentro de `CODEX APPS` y apunta a este panel.

Durante el arranque el estado queda en amarillo mientras se valida la configuracion y la conexion con Telegram. Si el proceso falla, el panel abre la pestana de logs y muestra el error de inicio.

Para reconstruir el lanzador de Windows ejecutá `powershell -ExecutionPolicy Bypass -File build_control_panel.ps1`. El build regenera el ICO multirresolución desde el PNG fuente, compila el lanzador y actualiza el acceso directo de `CODEX APPS`.

El build tambien crea `Galerazo Bot - Logs.lnk` en `CODEX APPS`: abre una consola que sigue los logs de produccion por IAP y se detiene con `Ctrl+C`. El bot emite logs desde `DEBUG`, pero el lanzador omite los polls exitosos repetitivos de `getUpdates`; los errores y el resto del trafico se mantienen visibles. Actualiza `Galerazo Bot.lnk` en el Escritorio. Volve a ejecutar el setup si moves el repositorio, cambias el runtime o necesitas regenerar los accesos con las rutas actuales.

Las dependencias directas se declaran en `requirements.in`. `requirements.txt` fija todas las versiones directas y transitivas para que Windows y Docker instalen el mismo conjunto reproducible.

### Actualizaciones y rollback

El workflow `Update runtime and dependencies` corre semanalmente y tambien se puede iniciar manualmente. Usa la ultima version estable disponible de Python, resuelve las ultimas releases estables de `requirements.in` y valida:

- alineacion entre `.python-version` y Docker;
- suite completa en Python nativo;
- compilacion y `pip check`;
- build y suite completa dentro de Docker.

Solo despues de esas validaciones crea y fusiona la actualizacion. Si algun paso falla, el workflow termina antes de modificar `main`, por lo que el estado anterior queda activo.

Si no encuentra cambios de runtime o dependencias, omite la suite y el build Docker para no consumir minutos innecesarios.

### CI y consumo de GitHub Actions

- `Quality` ejecuta la suite Linux solo ante cambios sustantivos. Commits limitados a Markdown o `.gitignore` no generan un run.
- Pushes nuevos a la misma rama cancelan un run anterior que todavia este activo.
- `Docker quality` corre solo cuando cambian Dockerfile, `.python-version`, dependencias o la configuracion del propio workflow. Tambien puede iniciarse manualmente.
- El deploy desactivado es exclusivamente manual y no crea runs omitidos en cada push.
- Los jobs tienen timeouts de 10, 15 y 20 minutos para evitar consumo indefinido ante un bloqueo.

### Pruebas locales y cobertura

La validacion local rapida y la cobertura reproducible se ejecutan dentro de `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m coverage erase
.\.venv\Scripts\python.exe -m coverage run -m pytest
.\.venv\Scripts\python.exe -m coverage json
.\.venv\Scripts\python.exe scripts\check_coverage.py
.\.venv\Scripts\python.exe -m coverage report
```

`pytest` es el runner oficial y recoge tambien las pruebas existentes basadas en `unittest`, incluidos los casos `IsolatedAsyncioTestCase`; `pytest-asyncio` queda configurado para futuros tests async nativos. `coverage.py` mide sentencias/lineas y ramas; este stack no expone una metrica separada de funciones. Ambos minimos son 100% y cualquier linea o rama nueva sin prueba hace fallar la validacion. `galerazo_bot/control_panel.py` se excluye de la metrica multiplataforma porque su prueba de layout requiere Tk nativo de Windows y se ejecuta localmente; sus demas contratos siguen cubiertos por pruebas estaticas. `Quality` ejecuta la suite una sola vez bajo cobertura. La validacion Docker se activa solamente cuando cambia el runtime, el lock o el contenedor, y los workflows de deploy costosos siguen siendo manuales.

Si aparece un problema despues de fusionar una actualizacion, ubica ese commit y revertirlo conserva el historial:

```powershell
git log -- .python-version Dockerfile requirements.txt
git revert <commit-de-actualizacion>
powershell -ExecutionPolicy Bypass -File scripts/sync_windows_runtime.ps1
git push
```

El sincronizador toma automaticamente la version restaurada desde `.python-version`.

## Configuracion inicial

### 1. Crear el bot en Telegram

1. Abri Telegram y hablale a `@BotFather`.
2. Ejecuta `/newbot`.
3. Elegi nombre y username para el bot.
4. Copia el token que te da BotFather.
5. Pega ese token en `.env`:

```env
TELEGRAM_BOT_TOKEN=token-de-botfather
```

### 2. Configurar devs

Los comandos sensibles solo los pueden usar los devs. Agrega tu user id de Telegram en `.env`:

```env
TELEGRAM_DEV_USER_IDS=<tu-user-id>
```

Si hay mas de un dev, separalos por coma:

```env
TELEGRAM_DEV_USER_IDS=<tu-user-id>,<otro-user-id>
```

Para conseguir tu user id podes usar `/debug` una vez que el bot este corriendo y te hayas configurado, o usar un bot externo de Telegram que muestre tu id.

### 3. Configurar canal de logging

El canal de logging recibe solo los eventos que definamos explicitamente. Por ahora registra:

- Inicio del bot.
- Errores no handleados.

Para configurarlo:

1. Crea un canal o grupo privado para logs.
2. Agrega el bot.
3. Dale permiso para enviar mensajes.
4. Configura el id del chat en `.env`:

```env
TELEGRAM_LOG_CHAT_ID=<id-del-chat-de-logs>
```

### 4. Configurar canal de anuncios

El canal de anuncios recibe las novedades enviadas con `/novedad mensaje`.

Para configurarlo:

1. Crea un canal o grupo para anuncios.
2. Agrega el bot.
3. Dale permiso para enviar mensajes.
4. Configura el id del chat en `.env`:

```env
TELEGRAM_ANNOUNCEMENTS_CHAT_ID=<id-del-chat-de-anuncios>
```

### 5. Configurar la base de datos

SQLite se crea automaticamente cuando arranca el bot. Por defecto usa:

```env
DATABASE_PATH=data/galerazo.sqlite3
```

Podes cambiar esa ruta si queres guardar la base en otro lugar.

### 6. Archivo `.env` completo

Ejemplo:

```env
TELEGRAM_BOT_TOKEN=token-de-botfather
OPENAI_API_KEY=clave-restringida-de-moderacion
TELEGRAM_DEV_USER_IDS=
TELEGRAM_LOG_CHAT_ID=
TELEGRAM_ANNOUNCEMENTS_CHAT_ID=
TELEGRAM_HISOPO_COMMON_FILE_ID=file-id-del-hisopo-comun
TELEGRAM_HISOPO_SILVER_FILE_ID=file-id-del-hisopo-plateado
TELEGRAM_HISOPO_GOLD_FILE_ID=file-id-del-hisopo-dorado
TELEGRAM_HISOPO_DIAMOND_FILE_ID=file-id-del-hisopo-diamante
TELEGRAM_HISOPO_FLEETING_FILE_ID=file-id-del-hisopo-fugaz
TELEGRAM_HISOPO_MYSTERY_FILE_ID=file-id-del-hisopo-misterioso
TELEGRAM_HISOPO_PUTRID_FILE_ID=file-id-del-hisopo-putrefacto
TELEGRAM_HISOPO_RADIOACTIVE_FILE_ID=file-id-del-hisopo-radiactivo
TELEGRAM_HISOPO_FAKE_FILE_ID=file-id-del-hisopo-falso
TELEGRAM_HISOPO_TWIN_FILE_ID=file-id-del-hisopo-gemelo
TELEGRAM_HISOPO_GIANT_FILE_ID=file-id-del-hisopo-gigante
TELEGRAM_HISOPO_MIRACLE_FILE_ID=file-id-del-hisopo-milagroso
DATABASE_PATH=data/galerazo.sqlite3
GOOGLE_SHEETS_CREDENTIALS_JSON_PATH=secrets/google-service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID=replace-with-spreadsheet-id
GOOGLE_SHEETS_WORKSHEET_NAME=Gastos
GOOGLE_CLOUD_BILLING_PROJECT_ID=bot-fleet-production
GOOGLE_CLOUD_BILLING_TABLE=bot-fleet-production.billing_export.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX
GOOGLE_CLOUD_BILLING_REPORT_TIME=09:00
```

El archivo `.env` no se sube al repo.

### 7. Configurar Google Sheets para gastos

El sistema de gastos usa estas variables:

```env
GOOGLE_SHEETS_CREDENTIALS_JSON_PATH=secrets/google-service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID=replace-with-spreadsheet-id
GOOGLE_SHEETS_WORKSHEET_NAME=Gastos
```

Si faltan credenciales o `GOOGLE_SHEETS_SPREADSHEET_ID`, el bot igual guarda los gastos en SQLite y los deja pendientes de sincronizacion para subirlos despues.

### 8. Configurar moderacion de triggers

La moderacion es opcional y usa el endpoint gratuito de OpenAI Moderation. Crea una API key de proyecto restringida, concede permiso de escritura solamente a `/v1/moderations` y cargala en la pestana `Configuracion` del panel, en `Clave de moderacion OpenAI`. Tambien se puede configurar directamente:

```env
OPENAI_API_KEY=clave-restringida-de-moderacion
```

La clave se guarda exclusivamente en `.env`, que esta ignorado por Git. Reinicia el bot despues de agregarla. Sin clave, el bot no escanea ni bloquea media y conserva el comportamiento anterior.

La moderacion se ejecuta una sola vez al agregar el trigger. Fotos, documentos de imagen y stickers se analizan como imagen. Videos, documentos de video y videomensajes se analizan mediante cuatro frames ubicados al 20%, 40%, 60% y 80% de la duracion. El contenido descargado, las imagenes normalizadas y los frames viven solo en memoria y se liberan tanto ante exito como ante error; nunca se guardan en SQLite ni en archivos locales. Al reproducir un trigger no se vuelve a consultar la API.

Esta capa detecta contenido sexual general. No es un detector especializado ni una garantia de deteccion de material de abuso sexual infantil.

El Bot API oficial de Telegram limita `getFile` a 20 MB. Con moderacion activa, un archivo mayor se rechaza con un mensaje especifico porque el bot no puede descargarlo para analizarlo. Sin moderacion activa, ese limite no altera el guardado por `file_id`.

### 9. Configurar el reporte diario de gasto de Google Cloud

El bot usa `JobQueue.run_daily` de `python-telegram-bot` y la exportacion estandar de Cloud Billing a BigQuery. La API de Billing no expone el gasto mensual actual directamente.

1. En Google Cloud crea un dataset de BigQuery; para obtener backfill desde el mes anterior conviene la ubicacion multirregion `US`.
2. En `Facturacion > Exportacion de facturacion > Exportacion a BigQuery`, habilita `Costo de uso estandar` y selecciona ese dataset.
3. Espera a que Google cree la tabla `gcp_billing_export_v1_<BILLING_ACCOUNT_ID>`; la carga inicial puede tardar hasta cinco dias.
4. Concede a la service account de la VM `BigQuery Job User` en el proyecto que contiene el dataset y `BigQuery Data Viewer` solamente sobre ese dataset.
5. Configura el proyecto, la tabla completa y la hora argentina:

```env
GOOGLE_CLOUD_BILLING_PROJECT_ID=bot-fleet-production
GOOGLE_CLOUD_BILLING_TABLE=bot-fleet-production.billing_export.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX
GOOGLE_CLOUD_BILLING_REPORT_TIME=09:00
```

En GCE no se usa una clave JSON: el cliente toma Application Default Credentials de la service account adjunta a la VM. Localmente podes usar `gcloud auth application-default login` con una cuenta que tenga los mismos permisos.

Cada dia el canal de logging recibe gasto bruto, creditos, gasto neto y fecha de actualizacion para el mes de factura vigente. La consulta usa parametros, cache y un limite estricto de 100 MiB facturables. La exportacion y los reportes de Google pueden llevar mas de 24 horas de demora, por lo que este aviso complementa pero no reemplaza el presupuesto y sus alertas.

El dataset y los permisos minimos se pueden preparar de forma idempotente. El script exige reconocer que BigQuery es un recurso potencialmente facturable:

```powershell
.\scripts\deploy\Initialize-GceBillingReport.ps1 `
  -ProjectId bot-fleet-production `
  -DatasetId billing_export `
  -ServiceAccountId galerazo-vm `
  -AcknowledgeBillableResource
```

El script no habilita la exportacion de la cuenta de facturacion: ese paso se confirma manualmente en la consola.

## Canales del bot

- Canal operativo: chats, grupos y supergrupos donde los usuarios interactuan con el bot.
- Canal de logging: chat configurado en `TELEGRAM_LOG_CHAT_ID`.
- Canal de anuncios: chat configurado en `TELEGRAM_ANNOUNCEMENTS_CHAT_ID`.

Por ahora el canal de logging solo recibe:

- Un mensaje cuando se inicia el bot.
- Errores no handleados.
- Reportes enviados por usuarios con `/reportar`.
- Avisos cuando un mensaje no paginable supera el limite de Telegram y se envia truncado.
- Reporte diario del gasto mensual de Google Cloud cuando Billing esta configurado.

Los reportes de excepciones comienzan con `TipoDeExcepcion: detalle` para que la causa sea visible inmediatamente; debajo conservan el contexto, la update y el traceback completo para diagnostico.

El canal de anuncios recibe mensajes enviados por devs con:

```powershell
/novedad mensaje
```

## Reportar bugs

Los problemas de seguridad no deben publicarse en issues ni enviarse a chats compartidos. Usa el canal privado descrito en [SECURITY.md](SECURITY.md); los reportes funcionales comunes pueden seguir el flujo de abajo.

Cualquier usuario puede enviar un reporte al canal de logging con:

```powershell
/reportar mensaje
```

El bot reenvia el texto al canal configurado en `TELEGRAM_LOG_CHAT_ID` junto con metadata del usuario y del chat: `user_id`, username, nombre visible, `chat_id`, tipo de chat, titulo y `message_id`.

Para evitar abuso, cada usuario puede enviar como maximo un reporte por dia. Si Telegram convierte un grupo en supergrupo, la referencia al `chat_id` guardada para ese reporte diario se migra al nuevo id.

## Backups

Los devs pueden pedir un backup de la base con:

```powershell
/backup
```

El bot crea siempre una copia local en `backups/`. Si el archivo entra en el limite de subida del Bot API de Telegram, lo envia como documento respondiendo al comando. Si no entra, responde indicando que dejo el backup local.

## Debug

Los devs pueden inspeccionar el update crudo de Telegram con:

```powershell
/debug
```

Si el JSON entra en un mensaje de Telegram, el bot responde con texto. Si es demasiado largo, lo adjunta sin caption en un archivo llamado `Debug de la update {update_id}`.

## Estadisticas de chats

Cualquier usuario puede ver estadisticas de chats con:

```powershell
/chats
```

El reporte muestra:

- Total de chats.
- Chats activos o sin eliminacion detectada.
- Chats donde el bot fue eliminado, bloqueado o expulsado.
- El mismo desglose para chats privados, grupos, supergrupos y canales.

Cuando Telegram informa que un grupo migra a supergrupo, el bot actualiza el `chat_id` viejo al nuevo para no contar el mismo chat dos veces.

## La Galeraza

La Galeraza es un juego para grupos y supergrupos.

Reglas:

- Cada chat tiene su propia competencia.
- El usuario que manda el primer mensaje del día según el timestamp de Telegram gana 1 punto.
- El bot responde a ese mensaje con:

```text
Felicitaciones ganaste la Galeraza!
```

- El juego no corre en chats privados ni canales.
- Se puede deshabilitar por grupo desde `/config`. Si esta deshabilitada, no se detectan ganadores y `/galerazas` no responde en ese chat.

Ranking:

```powershell
/galerazas
```

Formato:

```text
Tabla de Galerazas
Nombre visible 1 (id1) => 5
Nombre visible 2 (id2) => 4
```

El ranking se ordena de mayor a menor puntaje. Usa el nombre visible guardado en SQLite y el user ID; no incluye `@alias`, por lo que no genera menciones. Los nombres se actualizan cuando el bot recibe nuevas updates de esos usuarios y el ranking no hace requests adicionales a Telegram.

### Orden y consistencia

El bot usa un `PerChatUpdateProcessor` basado en `BaseUpdateProcessor` de `python-telegram-bot`. Las updates de un mismo chat se procesan en orden FIFO, por lo que primero se aplican los efectos del mensaje entrante y despues se ejecuta un `/galerazas` posterior. Chats distintos pueden avanzar en paralelo y no se bloquean entre si.

El premio diario usa una transaccion `BEGIN IMMEDIATE` y una insercion atomica en SQLite (`INSERT OR IGNORE`) por chat y fecha. Si llegan dos mensajes candidatos muy cerca, solo el primero que se procese para ese chat y dia suma el punto. Las migraciones a supergrupo unen la secuencia del ID viejo con la del nuevo.

La fecha se calcula exclusivamente desde `message.date` de Telegram, convertido a `America/Argentina/Buenos_Aires` mediante `tzdata`; no usa la hora de recepción, el reloj local ni el timezone configurado en Windows, Docker o el servidor. Esto permite procesar updates pendientes después de una suspensión sin mover mensajes al día equivocado. Compiten los mensajes originales de usuarios humanos en grupos y supergrupos, incluidos eventos de servicio; no compiten ediciones, bots ni posts de canal.

## Recolector de Hisopos

El Recolector de Hisopos es un juego para grupos y supergrupos y viene habilitado por defecto. Un admin o dev puede desactivarlo desde `/config`, en `Comandos -> Recolector de Hisopos`, y elegir una de cinco intensidades:

`/reglashisopo` resume dentro de Telegram las probabilidades, vencimientos, premios y penalizaciones de todos los tipos. `/hisopos` muestra la tabla de puntajes del grupo, incluidos los jugadores que todavía tienen cero puntos. `/coleccionhisopos` muestra la colección histórica del usuario que lo ejecuta; si se usa respondiendo a otra persona, muestra la colección de esa persona.

- muy poca: 1 % por mensaje válido;
- poca: 5 %;
- media: 10 %;
- alta: 15 %;
- muy alta: 20 %.

Cada mensaje original de un usuario humano que podría competir por La Galeraza genera una tirada de 1 a 100. Si la tirada entra en el porcentaje configurado, aparece un hisopo con foto y el botón `Capturar hisopo`. Las ediciones y los mensajes de bots no generan tiradas.

Antes de publicar una nueva aparición, el bot intenta borrar en ese mismo grupo los mensajes de Hisopos con más de 24 horas para no acumularlos indefinidamente en Multimedia. Los `message_id` y el estado de la limpieza se conservan en SQLite y migran junto con el grupo. Un fallo de Telegram queda registrado y nunca impide enviar el Hisopo nuevo; se reintenta hasta tres veces con al menos 10 minutos entre intentos. Telegram solo permite borrar mensajes de menos de 48 horas: los que ya superaron esa ventana se descartan de la cola interna y quedan visibles, sin nuevos intentos ni afectar su registro histórico.

Una segunda y única tirada de `1` a `10.000` define la rareza, pero se hace solamente después de que la intensidad decidió que habrá una aparición. No existen tiradas previas independientes para los especiales. Los rangos no se superponen y suman el 100 %:

| Tirada | Aparición | Tipo sorteado | Qué muestra al aparecer | Efecto al capturarlo |
| --- | ---: | --- | --- | --- |
| 1-4665 | 46,65 % | común | imagen y valor del común | suma 1 punto |
| 4666-6065 | 14 % | plateado | imagen y valor del plateado | suma 2 puntos |
| 6066-7065 | 10 % | dorado | imagen y valor del dorado | suma 3 puntos |
| 7066-7765 | 7 % | fugaz | imagen y valor del fugaz | suma 5 puntos; se pudre en 1 minuto |
| 7766-8465 | 7 % | misterioso | imagen de misterioso y valor oculto | contiene uno de los otros once tipos y aplica su efecto |
| 8466-8965 | 5 % | putrefacto | se disfraza de común, plateado, dorado o diamante | revela el putrefacto, resta 2 puntos y puede dejar puntaje negativo |
| 8966-9365 | 4 % | radiactivo | imagen de radiactivo y valor oculto | calcula al capturarlo `-3`, `-1`, `2`, `4` o `6` según el tiempo transcurrido |
| 9366-9665 | 3 % | falso | se disfraza de común, plateado, dorado o diamante | revela el falso, vale 0 y no agenda para el día siguiente |
| 9666-9865 | 2 % | gemelo | imagen y valor del gemelo | suma 4 puntos, lanza otro hisopo en el momento y agenda uno para el día siguiente |
| 9866-9965 | 1 % | diamante | imagen y valor del diamante | suma 10 puntos |
| 9966-9990 | 0,25 % | gigante cooperativo | imagen, premio y progreso del gigante | requiere cooperación; cada participante gana 4 puntos si se completa |
| 9991-10000 | 0,10 % | milagroso | imagen del milagroso y valor oculto | suma el máximo entre 15 puntos y la mitad del puntaje del líder actual |

Falso y Putrefacto eligen una segunda apariencia: común 75 %, plateado 14 %, dorado 10 % y diamante 1 %. Son los mismos pesos de esos tipos en la tirada normal, pero el Común absorbe el 28 % de Fugaz, Misterioso, Putrefacto, Radiactivo, Falso y Gemelo, que no pueden usarse como disfraz. Antes del clic se muestran la foto y el valor aparente de esa máscara; al capturarlos revelan su foto, tipo y resultado reales.

El Radiactivo dura 20 minutos y calcula su puntaje recién dentro de la captura atómica: `-3` desde 0:00 hasta 4:59, `-1` desde 5:00 hasta 9:59, `+2` desde 10:00 hasta 14:59, `+4` desde 15:00 hasta 17:59 y `+6` desde 18:00 hasta 19:59. Así permanece negativo durante exactamente la primera mitad y los niveles positivos más altos ocupan intervalos cada vez más cortos cerca del vencimiento. Su mensaje inicial oculta el valor; la edición posterior informa cuántos puntos ganó o perdió el capturador.

El Misterioso contiene uno de los otros once tipos, sin otro Misterioso adentro. La selección interna conserva sus pesos relativos: común 50,16 %, plateado 15,05 %, dorado 10,75 %, fugaz 7,53 %, putrefacto 5,38 %, radiactivo 4,30 %, falso 3,23 %, gemelo 2,15 %, diamante 1,08 %, gigante 0,27 % y milagroso 0,11 %. Su contenido y su valor permanecen ocultos hasta la captura. La envoltura Misteriosa siempre dura 20 minutos, incluso si contiene un Fugaz; en ese caso, los 5 puntos solo están disponibles durante el primer minuto. Desde el minuto 1 todavía puede reclamarse y revela el Fugaz, pero entrega 0 puntos y no agenda otra aparición. Si contiene un Gigante, la primera ayuda lo revela, cuenta como la primera participación y el grupo continúa viendo el progreso. Si la envoltura se pudre a los 20 minutos sin ninguna ayuda, no revela el contenido.

El Gigante cooperativo dura 20 minutos y requiere `min(15, miembros del chat - Galerazo)` participaciones únicas. En un chat con al menos 16 miembros pide 15 ayudas; en uno más pequeño usa el total que informa Telegram menos el propio Galerazo. Esa consulta entrega una cantidad, no una lista filtrada de personas, por lo que otros bots también pueden quedar incluidos en la meta de los chats pequeños. Cada usuario puede ayudar una sola vez, la foto y el botón muestran el progreso y nadie recibe puntos parcialmente. Si alcanza el objetivo, cada participante gana 4 puntos y se programa una sola aparición total para el día siguiente; si se pudre incompleto, nadie gana ni pierde puntos y no se programa nada.

El Milagroso dura 20 minutos y calcula su premio al capturarlo: entrega el máximo entre 15 puntos y la mitad del puntaje del líder actual del grupo, redondeada hacia arriba. Por ejemplo, con un líder de 31 puntos entrega 16; con un líder de 20, cero o negativo entrega 15. El cálculo y la captura se realizan en la misma transacción, su valor inicial permanece oculto y programa una aparición para el día siguiente como una captura normal.

La primera callback procesada para ese chat reclama el premio dentro de una transacción inmediata de SQLite; las siguientes muestran un alerta de Telegram sin sumar. Al capturar un Falso, Putrefacto o Misterioso, el mismo mensaje reemplaza la foto por la del tipo real, informa el resultado y elimina la botonera. Salvo el Fugaz directo, a los 20 minutos el Hisopo se pudre, deja de valer y el mensaje pierde la botonera. Tocar un Fugaz después de su minuto no suma ni agenda nada: solamente informa que ya se pudrió. Si una rareza todavía no tiene todos los `file_id` que necesita para aparecer y revelarse, esa tirada usa el Hisopo común para no perder el evento.

La colección persiste por usuario y grupo sin temporadas ni reinicios. Guarda cuántos ejemplares se capturaron de cada uno de los 12 tipos. Desde la versión 0.34, cada Misterioso nuevo suma una unidad de Misterioso y otra del tipo que revela; si ocultaba un Fugaz reclamado después de su minuto, solo suma el Misterioso. Los Misteriosos anteriores no se reconstruyen retroactivamente. Cuando se completa un Gigante, todos los participantes agregan el Gigante y, si apareció oculto como Misterioso, también el Misterioso. Los tipos todavía no descubiertos se muestran con `❓` y los descubiertos con `✅`. La colección se migra y combina si Telegram convierte el grupo en supergrupo.

Un fallo al enviar la foto de una aparición no queda absorbido silenciosamente: conserva el contexto de chat, origen, tipo real y apariencia, se eleva al manejador de errores y se informa en el canal de logging configurado. Las apariciones programadas fallidas quedan marcadas como `failed` en vez de permanecer en procesamiento.

Cada captura programa una aparición adicional en un segundo aleatorio del día calendario siguiente de Argentina; el Falso no programa ninguna y el Gemelo, además de esa agenda normal, lanza una aparición nueva inmediatamente. Cada grupo puede acumular como máximo 10 apariciones con horario aleatorio para una misma fecha argentina: al completar el cupo, las capturas posteriores conservan sus puntos y efectos pero no agregan otra programación para ese día. El límite no se aplica a las apariciones activadas por mensajes ni a la aparición inmediata del Gemelo. La programación se guarda en SQLite y se reconstruye al iniciar el bot, por lo que sobrevive reinicios. Si el juego está deshabilitado cuando llega el horario, la aparición programada se cancela. Los Hisopos podridos no programan apariciones.

Las imágenes se envían mediante los `file_id` persistentes de Telegram configurados en:

```env
TELEGRAM_HISOPO_COMMON_FILE_ID=
TELEGRAM_HISOPO_SILVER_FILE_ID=
TELEGRAM_HISOPO_GOLD_FILE_ID=
TELEGRAM_HISOPO_DIAMOND_FILE_ID=
TELEGRAM_HISOPO_FLEETING_FILE_ID=
TELEGRAM_HISOPO_MYSTERY_FILE_ID=
TELEGRAM_HISOPO_PUTRID_FILE_ID=
TELEGRAM_HISOPO_RADIOACTIVE_FILE_ID=
TELEGRAM_HISOPO_FAKE_FILE_ID=
TELEGRAM_HISOPO_TWIN_FILE_ID=
TELEGRAM_HISOPO_GIANT_FILE_ID=
TELEGRAM_HISOPO_MIRACLE_FILE_ID=
```

Los artes fuente y sus indicaciones de generación están en [`assets/hisopos`](assets/hisopos/README.md). Para obtener cada valor, enviá la imagen al bot como foto y respondé ese mensaje con `/debug`. En el JSON, usá el `file_id` de la última entrada de `message.photo`, que corresponde al mayor tamaño. El campo `file_unique_id` no sirve para reenviar archivos. Reiniciá el bot local después de guardar los valores necesarios en `.env`.

## Configuracion por grupo

`/config` abre un tablero con opciones del grupo o supergrupo. Solo pueden usarlo admines del chat, quien agrego el bot o devs. Los botones del tablero tambien validan ese nivel de permisos cada vez que se tocan.

Menu principal:

- `Idioma`: permite elegir Español (Argentina o España), English, Русский, Latine, 日本語, Italiano, Français, Deutsch, Nederlands, 中文 (简体 o 繁體), Português (Brasil o Portugal), Català, Euskara o Avañe'ẽ. El idioma actual aparece marcado entre corchetes.
- `Comandos`: muestra los conjuntos de comandos configurables por grupo.

Todos los submenus tienen un boton `< Atrás`. El menu principal no tiene boton de volver.

Todos los niveles del menu incluyen una X roja para cerrar y eliminar el mensaje de configuracion. Igual que el resto del tablero, solo pueden usarla admines del chat, quien agrego el bot o devs.

El idioma por defecto siempre es español de Argentina. Si un grupo cambia de idioma, los textos que el bot muestra o envia en ese grupo se localizan: respuestas de comandos, menús, popups de botoneras, backups/debug captions y mensajes de La Galeraza. Los nombres de los comandos se mantienen sin traducir.

Los conjuntos configurables son `Galeraza`, `Recolector de Hisopos`, `Triggers` y `Ruleta rusa`. Cada submenú muestra:

```text
¿Habilitado?
[ Sí ] - No
```

`Galeraza`, `Triggers` y `Recolector de Hisopos` vienen habilitados por defecto. `Ruleta rusa` permanece deshabilitada hasta que un admin o dev del chat la habilite. El Recolector también permite elegir la intensidad de apariciones. Una desactivación explícita del juego se conserva. La configuración, puntajes, colección histórica, hisopos activos y apariciones programadas se guardan en SQLite y se migran si Telegram convierte un grupo en supergrupo.

`/help` muestra todos los comandos correspondientes al nivel del usuario, incluidos los conjuntos configurables que estén apagados. Que aparezcan en la ayuda no evita que el bot respete la configuración del chat al intentar ejecutarlos.

Si el ranking o cualquier lista configurable supera el limite maximo de caracteres por mensaje de Telegram, el bot lo pagina sin cortar renglones. La botonera tiene hasta 5 botones de paginas. Ejemplos:

```text
1 - 2 - [ 3 ] - 4
<< - 6 - [ 7 ] - 8 - >>
```

La segunda fila de botones tiene:

- Candado cerrado: solo el usuario que ejecuto `/galerazas` puede abrirlo o cerrarlo. Al abrirlo, cualquier usuario puede usar la paginacion.
- X roja: elimina el mensaje y borra la metadata de esa botonera. Solo pueden usarla el usuario que ejecuto `/galerazas` o un dev.

Mientras el candado esta cerrado, solo pueden cambiar paginas el usuario que ejecuto `/galerazas` y los devs.

## Listas paginadas

El bot tiene una botonera generica para comandos que devuelven listas largas. Si una respuesta supera el limite maximo de caracteres por mensaje de Telegram, el bot:

- Divide el texto por renglones sin cortar ninguno al final de pagina.
- Guarda metadata de la botonera en SQLite.
- Muestra hasta 5 botones de paginas.
- Permite paginar solo al usuario que pidio la lista y a devs mientras el candado esta cerrado.
- Permite abrir y cerrar el candado. Al abrirlo muestra el popup `habilitado para todos`; al cerrarlo muestra `deshabilitado para todos`.
- Permite borrar el mensaje y su metadata con la X roja, solo al usuario original o a devs.
- Si alguien toca una botonera creada hace mas de 2 semanas, el bot intenta eliminar el mensaje, borra la metadata y muestra el popup `mensaje eliminado`.
- Si alguien toca una botonera cuya metadata ya no existe en SQLite, el bot intenta eliminar el mensaje y muestra el popup `mensaje eliminado`.
- Al iniciar, el bot tambien busca metadata de botoneras con mas de 2 semanas, intenta eliminar esos mensajes y siempre borra la metadata local.

Esto ya aplica a `/galerazas` y a cualquier comando que devuelva una respuesta larga, por ejemplo `/listanegra`.

## Triggers

Los triggers funcionan solo en grupos y supergrupos. Se pueden deshabilitar por grupo desde `/config` dentro de `Comandos -> Triggers`. Si estan deshabilitados, no funcionan los comandos del grupo y tampoco se disparan mensajes por triggers.

Para agregar uno:

```powershell
/agregartrigger nombre del trigger
```

Tambien existe el alias:

```powershell
/agrtrigger nombre del trigger
```

El comando se usa respondiendo a un mensaje válido. El nombre tiene que tener entre 5 y 32 caracteres, puede contener espacios y no puede repetirse en el mismo chat. El bot guarda el contenido para enviar un mensaje nuevo cuando otro mensaje del chat contenga ese texto.

Tipos soportados:

- Texto.
- Imagenes.
- Animaciones y GIFs.
- Videos.
- Audios y musica.
- Documentos.
- Videomensajes.
- Stickers.
- Dados y otros emojis animados soportados por `send_dice` de Telegram.
- Contactos.
- Ubicaciones y lugares.
- Encuestas reproducibles.

Si el mensaje tiene caption, el bot tambien guarda esa caption. Para media, se guarda el `file_id` de Telegram y el tipo interno de media para saber que metodo usar al enviarlo.

Cuando `OPENAI_API_KEY` esta configurada, el bot modera la media antes de escribir el trigger. Una imagen marcada como sexual se rechaza. En videos y videomensajes se moderan cuatro frames equidistantes. Si la descarga, extraccion o consulta falla, ese intento no se guarda y se puede reintentar mas tarde. La reproduccion de triggers aceptados no agrega consultas ni latencia de moderacion.

Los eventos de servicio, como el ingreso de un usuario, no se pueden agregar porque el bot no puede recrearlos. Tampoco se aceptan mensajes que requieren configuración externa no portable, como facturas, pagos o juegos registrados por otro bot.

Para borrar:

```powershell
/borrartrigger nombre del trigger
/eliminartrigger nombre del trigger
/eltrigger nombre del trigger
```

Para listar:

```powershell
/triggers
```

La lista se pagina automaticamente si supera el limite de Telegram. Si Telegram convierte el grupo en supergrupo, los triggers guardados se migran al nuevo `chat_id`.

## Ruleta rusa

La ruleta rusa funciona solo en grupos y supergrupos y viene deshabilitada por defecto. Un admin o dev puede habilitarla desde `/config`, en `Comandos -> Ruleta rusa`.

```powershell
/ruletarusa
```

- Cada usuario y chat conserva una partida persistente de seis recámaras con una bala aleatoria.
- Cada uso consume la siguiente recámara y muestra cuántos intentos quedan como máximo.
- Si sale la bala, el estado se reinicia y el bot expulsa al objetivo. La expulsión es reversible por un admin.
- Usuarios comunes siempre se apuntan a sí mismos. Admines y devs pueden responder al mensaje de otro usuario para apuntarlo.
- El bot, los admines y los devs son inmunes al efecto de expulsión.
- Antes de cada jugada, el bot verifica que sea administrador y tenga permiso para restringir usuarios.
- El estado se migra al nuevo `chat_id` cuando un grupo pasa a supergrupo.

## Gastos

Los gastos funcionan solo en grupos y supergrupos. Para chats nuevos vienen deshabilitados por defecto. Un usuario de nivel 2 o superior puede habilitarlos con:

```powershell
/habilitargastos
```

Y deshabilitarlos con:

```powershell
/deshabilitargastos
```

Tambien aparecen en `/config` dentro de `Comandos -> Gastos`.

Cuando el sistema esta habilitado, cualquier usuario del chat puede registrar gastos con este formato:

```powershell
/gasto monto | medio de pago | origen | descripcion
```

Ejemplo:

```powershell
/gasto 18500 | transferencia | caja del grupo | pizzas de la juntada
```

El bot guarda monto, moneda, medio de pago, origen, descripcion, usuario, chat, fecha y estado de sincronizacion.

Comandos utiles:

```powershell
/ultimosgastos
/estadogastos
/sincronizargastos
```

`/ultimosgastos` devuelve los ultimos gastos del chat. `/estadogastos` muestra si el grupo tiene gastos habilitados, si Google Sheets esta listo y cuantos pendientes hay. `/sincronizargastos` intenta subir los pendientes.

Si Google Sheets no esta configurado todavia, `/gasto` guarda igual en SQLite y lo deja pendiente. Si Telegram convierte el grupo en supergrupo, los gastos guardados migran al nuevo `chat_id`.

## Salir de un grupo

Los devs pueden hacer que el bot salga de un grupo o supergrupo con:

```powershell
/salir
```

Este comando solo funciona si el dev responde a un mensaje del bot con `/salir`.
Si se usa sin responder, el bot explica el uso correcto. Si lo usa alguien que no es dev, responde que no tiene permisos.

## Niveles de usuario

- `common`: cualquier usuario.
- `admin`: admin del grupo/supergrupo o la persona que agrego el bot a ese chat.
- `dev`: usuarios definidos en `TELEGRAM_DEV_USER_IDS`.

El comando `nivel` muestra que nivel detecta el bot para el usuario actual.

## Lista negra

Los usuarios bloqueados no pueden interactuar con el bot: no procesan comandos ni callbacks.

Los comandos de lista negra solo responden a devs:

```powershell
/bloquear
/bloquear @alias
/bloquear 123456789
/desbloquear
/desbloquear @alias
/desbloquear 123456789
/listanegra
/bloqueados
```

`/bloquear` y `/desbloquear` sin argumentos se usan respondiendo al mensaje del usuario objetivo.
Los `@alias` se resuelven contra usuarios que el bot ya haya visto.
Si `/listanegra` supera el limite de caracteres de Telegram, el bot pagina la lista con botonera.
Las listas de usuarios muestran siempre el nombre visible y el ID entre paréntesis, por ejemplo `Nombre visible (123456789)`. No incluyen `@`, así que no generan menciones.

## Restricciones por chat

En grupos y supergrupos, los usuarios de nivel 2 o superior pueden restringir usuarios solo para ese chat:

```powershell
/restringir
/restringir @alias
/restringir 123456789
/habilitar
/habilitar @alias
/habilitar 123456789
/restringidos
```

`/restringir` y `/habilitar` sin argumentos se usan respondiendo al mensaje del usuario objetivo. Un usuario restringido en un chat no puede interactuar con el bot en ese chat: no procesa comandos, callbacks, Galeraza ni triggers. Esto no lo bloquea globalmente en otros chats.

`/restringidos` muestra la lista con paginacion si supera el limite de Telegram. Si Telegram convierte el grupo en supergrupo, las restricciones se migran al nuevo `chat_id`.

## Probar localmente sin Telegram

```powershell
python -m galerazo_bot.cli hola
python -m galerazo_bot.cli help
python -m galerazo_bot.cli nivel
```

Esto tambien inicializa la base SQLite en `data/galerazo.sqlite3`.
La base usa solo la libreria estandar de Python.

## Correr el bot

```powershell
python app.py
```

El bot usa polling contra la Bot API de Telegram, asi que no necesitas exponer un webhook publico para empezar.
El polling usa explicitamente `drop_pending_updates=False`: al volver a encenderse procesa las updates que Telegram todavia conserve. Las updates que Telegram ya haya descartado por antiguedad no se pueden recuperar.

## Hosting y deploy

La opcion recomendada es Google Compute Engine con una VM `e2-micro`, Docker
Compose y disco persistente. El bot no publica puertos: Telegram se consulta por
polling y la administracion entra por SSH encapsulado en IAP.

El repositorio deja preparados dos productores de la misma imagen `linux/amd64`:

- **Local, recomendado para ahorrar CI:** `scripts/deploy/Build-DockerImage.ps1`
  prueba y construye en Docker Desktop; `Publish-DockerImage.ps1` la publica en
  Artifact Registry desde la PC.
- **GitHub manual:** `Publish GCE image` solo aparece bajo `workflow_dispatch`.
  Nunca construye ni publica una release por cada push.

En la VM, `compose.production.yaml` ejecuta el bot sin privilegios, con filesystem
de solo lectura, volumenes persistentes, healthcheck, rotacion de logs y restart.
Cada deploy crea un backup SQLite consistente y restaura la imagen anterior si
la nueva no llega a estado healthy.

La preparacion completa de Google Cloud, los comandos locales, la publicacion
manual desde GitHub, el primer deploy y el rollback estan en
[`docs/DEPLOY_GCE.md`](docs/DEPLOY_GCE.md).

La base de producción también tiene backups externos mensuales, consistentes e
independientes de Docker, con retención de 400 días en Cloud Storage. El diseño,
costos, seguridad, operación, restauración y procedimiento reutilizable para
otros bots están en [`docs/BACKUPS_GCE.md`](docs/BACKUPS_GCE.md).

Railway permanece como alternativa y su workflow historico sigue desactivado;
no forma parte del camino recomendado actual.

## Checklist para arrancar

- Crear bot con BotFather.
- Copiar `.env.example` a `.env`.
- Completar `TELEGRAM_BOT_TOKEN`.
- Completar `TELEGRAM_DEV_USER_IDS`.
- Agregar el bot al canal/grupo de logging y configurar `TELEGRAM_LOG_CHAT_ID`.
- Agregar el bot al canal/grupo de anuncios y configurar `TELEGRAM_ANNOUNCEMENTS_CHAT_ID`.
- Ejecutar `python app.py`.
- Probar `/hola`, `/nivel`, `/debug` y `/backup`.
