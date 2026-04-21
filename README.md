# Galerazo Bot

Base para un bot de Telegram en Python con `python-telegram-bot` y SQLite.

## Comandos

- `help` / `ayuda`: muestra los comandos disponibles para tu nivel de usuario.
- `hola`: responde un saludo.
- `nivel`: muestra el nivel detectado para el usuario.
- `bloquear`: bloquea un usuario. Solo devs.
- `desbloquear` / `desloquear`: desbloquea un usuario. Solo devs.
- `listanegra`: muestra los usuarios bloqueados. Solo devs.
- `novedad`: envia una noticia al canal de anuncios. Solo devs.
- `backup`: responde con un backup de SQLite. Solo devs.
- `debug`: responde con el objeto update del mensaje. Solo devs.
- `chats`: muestra estadisticas de chats por estado y tipo.
- `galerazas`: muestra el ranking de La Galeraza en grupos/supergrupos.
- `salir`: hace que el bot salga de un grupo o supergrupo. Solo devs.

Tambien acepta comandos con prefijo, por ejemplo `!help`, `/ayuda` o `/hola`.

## Estructura de comandos

Los handlers reales de Telegram se registran en `galerazo_bot/telegram_bot.py` con `CommandHandler`, `MessageHandler`, `CallbackQueryHandler` y `ChatMemberHandler`.

El dispatcher de comandos esta en `galerazo_bot/commands.py`. Ese archivo normaliza el texto, valida permisos y ejecuta el handler de dominio registrado.

Los comandos especificos estan en `galerazo_bot/command_handlers/`. Cada archivo contiene el handler y sus metodos auxiliares. Para agregar un comando nuevo:

1. Crear un archivo nuevo en `galerazo_bot/command_handlers/`.
2. Definir un diccionario `COMMANDS` con los nombres/aliases que activa ese archivo.
3. Importar ese `COMMANDS` en `galerazo_bot/command_handlers/__init__.py` y sumarlo al diccionario central.

El handler de dominio de `/hola` esta en `galerazo_bot/command_handlers/hola.py`. El `CommandHandler` de Telegram que lo activa se registra en `galerazo_bot/telegram_bot.py`.

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
pip install -r requirements.txt
```

La dependencia principal es `python-telegram-bot`, declarada en `requirements.txt`.

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
TELEGRAM_DEV_USER_IDS=123456789
```

Si hay mas de un dev, separalos por coma:

```env
TELEGRAM_DEV_USER_IDS=123456789,987654321
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
TELEGRAM_LOG_CHAT_ID=-1001234567890
```

### 4. Configurar canal de anuncios

El canal de anuncios recibe las novedades enviadas con `/novedad mensaje`.

Para configurarlo:

1. Crea un canal o grupo para anuncios.
2. Agrega el bot.
3. Dale permiso para enviar mensajes.
4. Configura el id del chat en `.env`:

```env
TELEGRAM_ANNOUNCEMENTS_CHAT_ID=-1009876543210
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
TELEGRAM_DEV_USER_IDS=123456789
TELEGRAM_LOG_CHAT_ID=-1001234567890
TELEGRAM_ANNOUNCEMENTS_CHAT_ID=-1009876543210
DATABASE_PATH=data/galerazo.sqlite3
```

El archivo `.env` no se sube al repo.

## Canales del bot

- Canal operativo: chats, grupos y supergrupos donde los usuarios interactuan con el bot.
- Canal de logging: chat configurado en `TELEGRAM_LOG_CHAT_ID`.
- Canal de anuncios: chat configurado en `TELEGRAM_ANNOUNCEMENTS_CHAT_ID`.

Por ahora el canal de logging solo recibe:

- Un mensaje cuando se inicia el bot.
- Errores no handleados.

El canal de anuncios recibe mensajes enviados por devs con:

```powershell
/novedad mensaje
```

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

Si el JSON entra en un mensaje de Telegram, el bot responde con texto. Si es demasiado largo, lo adjunta como archivo `.json`.

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
- El usuario que manda el primer mensaje del dia que recibe el bot en ese chat gana 1 punto.
- El bot responde a ese mensaje con:

```text
Felicitaciones ganaste la Galeraza!
```

- El juego no corre en chats privados ni canales.

Ranking:

```powershell
/galerazas
```

Formato:

```text
Galeraza!
usuario1 => 5
usuario2 => 4
```

El ranking se ordena de mayor a menor puntaje.

Si el ranking supera el limite maximo de caracteres por mensaje de Telegram, el bot lo pagina sin cortar renglones. La botonera tiene hasta 5 botones de paginas. Ejemplos:

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
```

`/bloquear` y `/desbloquear` sin argumentos se usan respondiendo al mensaje del usuario objetivo.
Los `@alias` se resuelven contra usuarios que el bot ya haya visto.
Si `/listanegra` supera el limite de caracteres de Telegram, el bot pagina la lista con botonera.

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

## Hosting gratuito

Para este bot hay dos requisitos importantes:

- Un proceso Python que pueda quedar corriendo en polling.
- Almacenamiento persistente para SQLite, porque la base vive en un archivo.

Opciones evaluadas:

- Railway: recomendado para empezar. Tiene volumen persistente en Free/Trial y alcanza para una SQLite chica. Monta el volumen en una ruta como `/data`.
- Render: no es buena opcion gratuita para SQLite persistente, porque el filesystem del servicio es efimero y los persistent disks son para servicios pagos.
- Koyeb: sirve para probar servicios gratis, pero las instancias free no pueden usar volumes y escalan a cero sin trafico; no encaja bien con polling + SQLite persistente.
- PythonAnywhere: la cuenta gratis no sirve bien para un bot siempre encendido; las always-on tasks son de cuentas pagas.
- Fly.io: tecnicamente sirve con volumes, pero hoy es trial/pay-as-you-go; no es la mejor opcion gratuita estable para este caso.

Recomendacion actual: Railway con un volumen montado en `/data`.

## Deploy en Railway

### 1. Preparar el repo

El proyecto incluye:

- `Dockerfile`: define como correr el bot.
- `.dockerignore`: evita subir `.env`, bases y backups al build.
- `.github/workflows/deploy.yml`: pipeline de deploy desactivado por ahora.

### 2. Crear proyecto en Railway

1. Crear una cuenta en Railway.
2. Crear un nuevo Project.
3. Crear un nuevo Service desde GitHub.
4. Seleccionar este repo.
5. Railway deberia detectar el `Dockerfile`.

### 3. Crear volumen persistente

1. En el proyecto de Railway, crear un Volume.
2. Asociarlo al service del bot.
3. Montarlo en:

```text
/data
```

4. Configurar la variable:

```env
DATABASE_PATH=/data/galerazo.sqlite3
```

Esto evita perder la base en redeploys.

### 4. Variables de entorno en Railway

Configurar estas variables en el service:

```env
TELEGRAM_BOT_TOKEN=token-de-botfather
TELEGRAM_DEV_USER_IDS=123456789
TELEGRAM_LOG_CHAT_ID=-1001234567890
TELEGRAM_ANNOUNCEMENTS_CHAT_ID=-1009876543210
DATABASE_PATH=/data/galerazo.sqlite3
```

`TELEGRAM_LOG_CHAT_ID` y `TELEGRAM_ANNOUNCEMENTS_CHAT_ID` pueden ser grupos o canales donde el bot tenga permiso para escribir.

### 5. Comando de arranque

El `Dockerfile` ya define:

```dockerfile
CMD ["python", "app.py"]
```

No hace falta configurar otro start command salvo que quieras sobrescribirlo desde Railway.

### 6. Deploy manual inicial

Para el primer deploy, usar el boton Deploy desde Railway.

Despues revisar logs del service. Si arranco bien, deberias ver que el bot manda al canal de logging:

```text
Galerazo Bot iniciado.
```

### 7. GitHub Actions para deploy automatico

El repo incluye `.github/workflows/deploy.yml`.

El workflow corre con push a `main`, pero esta desactivado por este flag:

```yaml
if: ${{ false }}
```

Cuando quieras activarlo, cambiarlo a:

```yaml
if: ${{ true }}
```

Antes de activarlo, configurar estos secrets en GitHub:

```text
RAILWAY_TOKEN
RAILWAY_SERVICE_ID
```

`RAILWAY_TOKEN` se crea en Railway desde Account Settings o Project Settings, segun el flujo que uses.
`RAILWAY_SERVICE_ID` es el id del service del bot.

El deploy automatico ejecuta:

```bash
railway up --service "$RAILWAY_SERVICE_ID" --detach
```

### 8. Checklist de deploy

- Repo en GitHub.
- Proyecto creado en Railway.
- Service conectado al repo.
- Volume creado y montado en `/data`.
- `DATABASE_PATH=/data/galerazo.sqlite3`.
- Variables de Telegram configuradas.
- Bot agregado al canal de logging.
- Bot agregado al canal de anuncios.
- Primer deploy manual probado.
- Secrets de GitHub configurados.
- El workflow sigue con `if: ${{ false }}` hasta que decidas activarlo.

## Checklist para arrancar

- Crear bot con BotFather.
- Copiar `.env.example` a `.env`.
- Completar `TELEGRAM_BOT_TOKEN`.
- Completar `TELEGRAM_DEV_USER_IDS`.
- Agregar el bot al canal/grupo de logging y configurar `TELEGRAM_LOG_CHAT_ID`.
- Agregar el bot al canal/grupo de anuncios y configurar `TELEGRAM_ANNOUNCEMENTS_CHAT_ID`.
- Ejecutar `python app.py`.
- Probar `/hola`, `/nivel`, `/debug` y `/backup`.
