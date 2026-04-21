# Galerazo Bot

Base inicial para un bot de Telegram en Python con comandos simples y SQLite.

## Comandos

- `help`: muestra los comandos disponibles.
- `hola`: responde un saludo.
- `nivel`: muestra el nivel detectado para el usuario.
- `bloquear`: bloquea un usuario. Solo devs.
- `desbloquear` / `desloquear`: desbloquea un usuario. Solo devs.
- `listanegra`: muestra los usuarios bloqueados. Solo devs.
- `novedad`: envia una noticia al canal de anuncios. Solo devs.
- `backup`: responde con un backup de SQLite. Solo devs.
- `debug`: responde con el objeto update del mensaje. Solo devs.

Tambien acepta comandos con prefijo, por ejemplo `!help` o `/hola`.

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

No hay dependencias externas obligatorias por ahora. Si mas adelante agregamos paquetes, van a quedar en `requirements.txt`.

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

## Checklist para arrancar

- Crear bot con BotFather.
- Copiar `.env.example` a `.env`.
- Completar `TELEGRAM_BOT_TOKEN`.
- Completar `TELEGRAM_DEV_USER_IDS`.
- Agregar el bot al canal/grupo de logging y configurar `TELEGRAM_LOG_CHAT_ID`.
- Agregar el bot al canal/grupo de anuncios y configurar `TELEGRAM_ANNOUNCEMENTS_CHAT_ID`.
- Ejecutar `python app.py`.
- Probar `/hola`, `/nivel`, `/debug` y `/backup`.
