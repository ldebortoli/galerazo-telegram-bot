# Integracion de la Mini App

El frontend se mantiene en el proyecto Galerazo web y se publica en
`https://galerazo.com/miniapp`. Este repositorio conserva solo la API aiohttp,
SQLite, firma/TTL de Telegram, precios, inventario y ledger de Stars. Los artes
que usa Telegram permanecen en `assets/hisopos/`; este servidor no los publica.
No existe modo preview ni respuesta simulada en el backend.

## Contrato

| Gateway web | Backend | Metodo |
| --- | --- | --- |
| `/miniapp/api/bootstrap?chat_id=all` | `/api/bootstrap?chat_id=all` | GET |
| `/miniapp/api/invoice` | `/api/invoice` | POST |
| `/miniapp/api/donor-visibility` | `/api/donor-visibility` | POST |

El Worker reenvia `X-Telegram-Init-Data` intacto y agrega
`X-Galerazo-Proxy-Secret`. El backend compara el secreto en tiempo constante
antes de despachar cualquier `/api/*`; sin secreto configurado devuelve 503,
con secreto incorrecto 403, y con sesion de Telegram ausente/invalida/vencida 401.
Los errores son JSON generico, con `Cache-Control: no-store`, igual que los
resultados. No se publican headers CORS, archivos estaticos ni rutas preview.
La clave debe tener entre 32 y 256 caracteres URL-safe. Generar
`secrets.token_urlsafe(32)` en un proceso privado, sin mostrar su salida.
El secreto compartido no sustituye la firma de Telegram.

La firma HMAC usa el token del bot real y la sesion dura como maximo una hora;
se rechazan fechas futuras, claves duplicadas, datos mayores a 8 KiB e IDs
invalidos. El contexto `a2` de `start_param` usa solo letras, digitos, guion y
guion bajo, y se firma para el usuario que pide
el enlace y el grupo. El parser sigue aceptando contextos `a1` historicos. No es un permiso compartible: un enlace reenviado a otra
persona no permite leer la coleccion original. Solo se consultan los albumes
que SQLite registra para el usuario autenticado; no se infiere pertenencia a
partir de un `chat_id` o `chat_instance` enviado por el cliente. La seleccion
explicita puede cambiar a otro album propio o a `all` despues de un enlace.

Facturas: JSON de hasta 16 KiB, `kind`, `item_key`, `source_chat_id` opcional y
`recipient` opcional. Precio, comprador y cantidad no son controlados por el
cliente; cada factura compra una unidad. Un grupo ajeno se rechaza; `all`
equivale a sin grupo de origen. Alias de regalo deben estar registrados; un ID
positivo puede identificar un destinatario nuevo. Club y donaciones no admiten
regalos. Crear una factura no acredita inventario ni registra un cobro.
Telegram confirma el pago por polling; se verifican firma, comprador, moneda
e importe y se aplica una vez por `telegram_payment_charge_id`.

La identidad editorial `Hisopo mosquito` usa `special-67` en la web y su SKU historico
en el gateway/ledger. No migrar claves, posesiones, precios ni cantidades. Las
facturas y confirmaciones del bot muestran tambien ese nombre editorial.
El bootstrap interno conserva el catalogo historico; el Worker filtra su
presentacion antes de enviarlo al navegador.

## Preparacion de activacion

No ejecutar estos pasos como parte de un push ordinario. La publicacion de una
imagen, el reinicio del bot y el anuncio de version requieren el flujo autorizado
de release de este proyecto. La web devuelve 503 hasta completar el corte.

1. Verificar `getMe.username == galerazo_bot`. Aplicar mediante el parcheador
   privado de configuracion el preset `deploy/gce/miniapp.env.example`, con el
   secreto real: URL `https://galerazo.com/miniapp`, nombre corto `hisopos`, host
   `127.0.0.1`, puerto 8080. No aplicar al bot local de pruebas. El arranque
   rechaza para ese dominio una identidad de pruebas, una URL diferente,
   ausencia de secreto o escucha fuera de loopback. Los inspectores solo
   muestran presencia booleana del secreto.
2. Crear un **tunel nombrado** en la cuenta Cloudflare existente, sin planes
   pagos, y un hostname HTTPS estable bajo `galerazo.com`. El candidato es
   `bot-api.galerazo.com`; el archivo de ejemplo no significa que ya exista.
   Aplicar `deploy/gce/miniapp-tunnel-config.example.json` a su configuracion
   remota y el CNAME proxied del hostname hacia `<tunnel-id>.cfargotunnel.com`.
   Solo las tres rutas indicadas llegan al backend; todo lo demas termina en
   404. No habilitar cache, captura de headers/payloads, niveles debug ni reglas
   que registren el secreto o initData. No usar un Quick Tunnel efimero.
3. Instalar una version estable verificada de `cloudflared` en la VM existente
   (fijar la version al activar). Crear un usuario de sistema dedicado
   `cloudflared` sin login. Guardar su token en
   `/etc/galerazo/cloudflared.token`, propietario `cloudflared:cloudflared`, modo
   0400, y copiar la unidad preparada como `galerazo-miniapp-tunnel.service`.
   Habilitar/iniciar esta unidad solamente durante el corte autorizado. El token
   nunca va en el comando, Git, mensajes o logs. El token de tunel es diferente
   del secreto proxy y no se entrega al Worker.
4. La unidad usa salida IPv6, HTTP/2 por TCP 7844 y metricas solo en loopback.
   La VM actual ya tiene Compose con red de host: `cloudflared` alcanza el
   `127.0.0.1:8080` del bot sin publicar puertos. No abrir firewall entrante,
   crear NAT, asignar IPv4, contratar servidor o cambiar de plan. Las sondas
   TCP IPv6 a ambas regiones de Cloudflare funcionaron el 2026-09-07; falta
   probar el tunel autenticado y su estabilidad. Cualquier alternativa paga
   necesita autorizacion expresa.
5. Guardar como **secrets** del Worker `galerazo-web`:
   `MINI_APP_API_ORIGIN=https://bot-api.galerazo.com` (solo tras verificar el
   hostname real) y `MINI_APP_PROXY_SECRET` (valor identico al bot). Mantener
   el rate limiter existente. No enviar el token de Telegram ni una copia de
   SQLite a Cloudflare. Coordinar esta escritura con la tarea web; no editar
   su checkout en paralelo.
6. Aprobar por separado el texto de `BROADCAST_CHANGELOG.md` y autorizar el
   release de esta version desde Bot Control Center. Verificar backup, guard,
   estado del servidor API y menu. No habilitar la URL en produccion 0.59:
   ese backend anterior todavia carece de la barrera del secreto proxy.

## Paso del propietario en BotFather

Desde la cuenta propietaria, abrir `@BotFather` y revisar `/myapps`. Si existe
la app corta `hisopos` de **@galerazo_bot**, editar su URL a
`https://galerazo.com/miniapp`. Si no existe, usar `/newapp`, elegir ese bot y
registrar la app con nombre corto `hisopos` y esa URL. Esto crea el enlace
`https://t.me/galerazo_bot/hisopos`. La Bot API no enumera ni crea estas apps
cortas: requiere la sesion del propietario, no el token del bot.

Opcionalmente configurar la Main Mini App en el perfil del mismo bot. Es una
entrada distinta de la app corta; su enlace es
`https://t.me/galerazo_bot?startapp`. No es requisito para los enlaces firmados
que genera `/coleccionhisopos`, que usan `/hisopos?startapp=<contexto>`.
El bot configura por `setChatMenuButton` el boton privado `Mis albumes` al
arrancar la integracion validada; no cambia las listas de comandos BotFather.
`/donar` ofrece el mismo frontend mediante un boton Web App en privado.

## Validacion y rollback

Local, sin Telegram real:

```sh
python scripts/runtime_versions.py
python -m coverage run -m pytest
python -m coverage report -m --fail-under=0
python -m coverage json --fail-under=0
python scripts/check_coverage.py
```

En Windows usar siempre `.venv/Scripts/python.exe`. El contrato HTTP real se
prueba con aiohttp TestServer/SQLite temporal: doble autenticacion, firma y TTL,
enlaces invalidos/ajenos, cambio de album, regalos, precios, privacidad,
acreditacion idempotente y ausencia de rutas del frontend. Las facturas,
confirmaciones y respuestas de Telegram son fixtures sin movimientos reales.
La suite existente cubre tambien renovaciones del Club y reembolsos. Docker
debe validar la imagen runtime sin `mini_app/` ni servidor estatico.

Tras el corte: sin secreto la API debe dar 403; con secreto correcto y sin
initData debe dar 401; desde Telegram abrir menu, enlace de grupo, cambiar
album y comprobar propiedad y privacidad. Probar tambien otro usuario y una
sesion vencida. La factura puede revisarse y cancelarse sin pagar. Ningun cobro
real sin autorizacion especifica; cualquier mensaje de prueba va exclusivamente
al chat de pruebas autorizado por la memoria local. Validar Android/iOS/Desktop,
safe areas, teclado y texto grande en la tarea web antes de dar el QA movil por
terminado.

Rollback: primero retirar los dos secrets del gateway y comprobar que devuelve
503, detener el tunel y desactivar `TELEGRAM_MINI_APP_URL` antes de restaurar una
imagen anterior. Mantener SQLite/ledger y no restituir copias antiguas de pagos.
Retirar/restaurar el menu privado segun corresponda. Nunca exponer 0.59 por el
tunel aun si el Worker parece funcionar. Estos pasos pertenecen al rollback
autorizado, no a las validaciones locales.

Fuentes: [Telegram Mini Apps](https://core.telegram.org/bots/webapps),
[edicion de apps mediante BotFather](https://core.telegram.org/api/bots/webapps),
[Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/),
[parametros IPv6, token-file y logs](https://developers.cloudflare.com/tunnel/advanced/run-parameters/),
[rutas de tunel](https://developers.cloudflare.com/tunnel/routing/).
