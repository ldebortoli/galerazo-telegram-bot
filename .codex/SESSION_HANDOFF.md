# Session handoff

## Objetivo general

Mantener Galerazo Bot reproducible en Windows, CI y Docker, con SQLite persistente y deploy seguro de bajo costo.

## Estado actual

- Confirmado y protegido por regresion que una captura de Hisopo edita la leyenda de la foto original con ganador, rareza y puntos, y elimina la botonera. Las rarezas negativas futuras deberan decir de forma localizada que el usuario perdio/resto puntos. No se eligio ni implemento aun ningun Hisopo especial adicional.
- Implementado localmente el Recolector de Hisopos, version `0.17`: configurable por grupo/supergrupo y deshabilitado por defecto; intensidades 1/5/10/15/20%; rarezas comun/plateada/dorada de 1/2/3 puntos; captura atomica, vencimiento a 20 minutos, `/hisopos`, 18 idiomas, migracion completa y agenda SQLite para el dia siguiente. Los artes de 1254x1254 estan en `assets/hisopos/`. BotFather ya incluye `/hisopos` en grupos es/en. No se construyo Docker, publico imagen ni desplego.
- Los tres `TELEGRAM_HISOPO_*_FILE_ID` aun no estan configurados. Para probar: enviar cada PNG al bot como foto, responder ese mensaje con `/debug`, copiar el `file_id` de la ultima entrada de `message.photo` al panel/.env y reiniciar el bot local. No usar `file_unique_id`.
- Todos los `send_message`, incluidos los `reply_text`, usan `RetryingExtBot`: ante `TimedOut` realizan tres intentos totales con esperas de 1 y 2 segundos, cortan al primer exito y registran/elevan el tercer fallo. Por preferencia explicita del usuario se prioriza entrega sobre evitar duplicados. La Galeraza conserva el punto y el error final informa los tres intentos tanto localmente como en el canal de logging. Version `0.16`; 244 pruebas y cobertura 100% OK. No se cambio ningun comando ni se desplego.
- Se compacto el selector de idiomas en filas de dos botones y las filas empatadas de `/galerazas` ahora usan un prefijo con guion alineado dentro de cada ancho de posicion. El guion es formato de salida, no una lista Markdown. Version `0.11`, commit `46cb093` pusheado a `main`; 236 pruebas y cobertura 100% OK. No hay deploy solicitado.
- Se incluyo debajo de la donacion la linea `Repo: https://github.com/ldebortoli/galerazo-telegram-bot` en el formato comun de anuncios y novedades. El control de longitud final se conserva para todos los idiomas. Version `0.12`; 236 pruebas y cobertura 100% OK. No hay deploy solicitado.
- El selector de idiomas de `/config` agrupa cuatro botones por fila para reducir su alto. Version `0.13`; la navegacion permanece en su propia fila. Validacion completa: 236 pruebas y cobertura 100% OK. No hay deploy solicitado.
- Se corrigio el prefijo espurio `rehegua` del catalogo guarani, eliminado solo al inicio de 199 textos. Version `0.14`; 237 pruebas y cobertura 100% OK. Se incorporo Quechua sureño (`quz`, Runa Simi), elegido por el usuario como la variante con mayor difusion; su catalogo es estatico. Version `0.15`; 238 pruebas y cobertura 100% OK.
- Corregido el workflow semanal `Update runtime and dependencies`: el target runtime no incluye `tests/`, por lo que pytest devolvia codigo 5. Ahora construye dicho target y verifica `ensure_python_version()`; la suite nativa se mantiene una sola vez. La ejecucion remota `31395803879` paso correctamente y creo `9a8a4b2` con el lock actualizado. Windows: 238 pruebas/cobertura 100%; Docker: 237 pruebas y una omision Tk esperada. No hay deploy solicitado.
- No hay tarea local activa. La suite usa `pytest==9.1.1` como runner oficial y `pytest-asyncio==1.4.0` en modo automatico. Conserva los tests heredados `unittest` e `IsolatedAsyncioTestCase`; setup Windows, Docker y CI ya ejecutan `python -m pytest`. Implementado en `6c35090` y pusheado a `main`; no requiere release ni deploy.
- La migracion grupo-supergrupo usa un `MessageHandler(filters.StatusUpdate.MIGRATE)` dedicado en el grupo 0 antes del preprocesador. SQLite reclama una vez la pareja de IDs y los migradores por dominio se ejecutan dentro de esa misma transaccion; el segundo evento de Telegram no modifica datos. Implementado en `209893d` y pusheado a `main`, sin release ni deploy.
- Se incorporaron catálogos completos estáticos para español de España, ruso, latín, japonés, italiano, francés, alemán, holandés, chino simplificado/tradicional, portugués de Brasil/Portugal, catalán, vasco y guaraní. Los comandos conservan sus nombres originales. Versión `0.10`; sin deploy solicitado.
- `USER_QUEUE.md` usa una unica seccion `Procesadas` para el historial y `Pendientes` para pedidos nuevos; se consolidaron las entradas historicas, incluido el `TimedOut` de `/triggers` y el formato de su lista, implementados desde `3fb6048`.
- Todo release, deploy o rollback de Galerazo se realiza desde Bot Control Center. Para una version nueva: vista Deploy, `Verificar`, luego `Publicar y deployar`; no sugerir PowerShell salvo fallo del panel y pedido explicito.
- Se implemento la version `0.9`, commit `54d6358` pusheado a `main`, sin release ni deploy solicitado. Todos los comandos requieren `/`, `!`, `.`, `>` o `$`; texto comun como `galerazas` no activa comandos. `handler_registration.py` concentra los handlers nativos PTB y `command_handlers/galerazas.py` contiene la adjudicacion y el envio de Galeraza. El `MessageHandler` de grupo 0 conserva la prioridad para cualquier mensaje humano, incluidos eventos de servicio.
- Las notas de release ahora acumulan entradas publicas no anunciadas: al desplegar `0.9` sobre el anuncio previo `0.7`, se enviaran juntos los cambios de `0.9` y `0.8`.
- Se implemento la version `0.8`, commit `9b4bf08` pusheado a `main`, aun sin release ni deploy solicitado. `/galerazas` ahora muestra posiciones competitivas, estado vacio y paginas autosuficientes al atravesar empates. Incluye tambien los cambios anteriores de `/apagar` exclusivo DEV con confirmacion privada de cinco minutos.
- Reinicio y apagado detienen polling, drenan las updates ya aceptadas durante un maximo de 60 segundos y fuerzan la accion si un handler no termina. El timeout se registra en logging. Docker da 65 segundos de gracia al detener el contenedor, por lo que un deploy sigue el mismo cierre ordenado antes del limite forzado.
- SQLite ahora posee `schema_migrations`. Las migraciones se aplican sobre el volumen remoto existente y quedan registradas; la primera elimina `galeraza_message_states`, ya copiada previamente a `paginated_message_states`. Un deploy normal hace backup remoto y nunca usa la SQLite local. `MigrateData` sigue siendo el unico flujo que la reemplaza.
- BotFather fue sincronizado con el token local. `/apagar` permanece oculto por ser DEV.
- Para futuras versiones, el changelog y el anuncio de release solo detallan cambios visibles en comandos publicos; los cambios DEV o internos se documentan fuera de esos canales publicos.
- Produccion ejecuta `galerazobot:a360a5d88272`, `running/healthy`. El deploy del 2026-07-29 anuncio correctamente la version `0.7`: los logs confirman los envios y `Novedades de la version 0.7 enviadas.`. El reporte diario de Google Cloud Billing sigue desactivado por falta de configuracion completa, no por un error de ejecucion.
- Pendiente de proximo deploy: la version `0.8` distribuira las mejoras publicas de `/galerazas`; el broadcast automatico enviara al canal de logging el resumen de enviados, omitidos, inactivos, fallidos y canal de anuncios. No afecta el anuncio ni se incluye en el changelog publico.
- `Galerazo Bot - Logs.lnk` fue creado en `C:\Users\calei\Documents\Codex\CODEX APPS`; sigue los logs remotos por IAP en PowerShell y se regenera con el setup/build.
- Pendiente de proximo deploy: el runtime emitira logs DEBUG y filtrara solamente los `getUpdates` HTTP 200 repetitivos. El acceso directo ya ejecuta el script actualizado.
- El bot local permanece apagado. No iniciar polling local con el token real mientras produccion esta activa.

## Validacion reciente

- Regresion del resultado de captura: 259 pruebas OK y cobertura 100% de sentencias/ramas; Python 3.14.7/lock, `pip check`, `compileall` y `git diff --check` OK. No hubo cambio funcional, version nueva, BotFather ni deploy.
- Version `0.17`: 259 pruebas nativas OK; cobertura 100% de sentencias y ramas; Python 3.14.7 y lock alineados tras integrar el actualizador remoto `70d0070`; `pip check`, `compileall`, parse PowerShell/Bash, tres imagenes cuadradas, `git diff --check` y checkpoint de logs OK. Docker Desktop no estaba iniciado, por lo que no hubo repeticion local del target Docker; sin release/deploy.
- Version `0.16`: 244 pruebas nativas OK; cobertura 100% de sentencias y ramas; `runtime_versions.py`, `pip check`, `compileall`, `git diff --check` y checkpoint de logs OK. Sin Docker por no cambiar runtime/contenedor; sin release/deploy.
- Pipeline runtime semanal: 238 pruebas nativas OK, cobertura 100% de sentencias y ramas, build y smoke test Docker runtime OK; `compileall`, `runtime_versions.py`, `pip check`, `git diff --check` y checkpoint de logs OK. Sin release/deploy.
- Version `0.15`: 238 pruebas nativas OK; cobertura 100% de sentencias y ramas; `compileall`, `runtime_versions.py`, `pip check`, `git diff --check` y checkpoint de logs OK. Sin release/deploy.
- Version `0.14`: 237 pruebas nativas OK; cobertura 100% de sentencias y ramas; `compileall`, `runtime_versions.py`, `pip check`, `git diff --check` y checkpoint de logs OK. Sin release/deploy.
- Version `0.13`: 236 pruebas nativas OK; cobertura 100% de sentencias y ramas; `compileall`, `runtime_versions.py`, `pip check`, `git diff --check` y checkpoint de logs OK. Sin release/deploy.
- Versión `0.10`: 234 pruebas nativas OK; cobertura 100% de sentencias y ramas; `compileall`, `runtime_versions.py`, `pip check`, `git diff --check` y checkpoint de logs OK. Sin release/deploy.
- Versión `0.12`: 236 pruebas nativas OK; cobertura 100% de sentencias y ramas; `compileall`, `runtime_versions.py`, `pip check`, `git diff --check` y checkpoint de logs OK. Sin release/deploy.
- Versión `0.11`: 236 pruebas nativas OK; cobertura 100% de sentencias y ramas; `compileall`, `runtime_versions.py`, `pip check`, `git diff --check` y checkpoint de logs OK. Sin release/deploy.
- 231 pruebas nativas OK; cobertura 100% de sentencias y ramas.
- Target Docker de tests: 224 pruebas OK, una prueba Tk omitida en Linux; runtime Docker de Python 3.14.6 validado.
- `scripts/runtime_versions.py`, `pip check`, `compileall` y `git diff --check` OK.

## Pendientes y bloqueos

- Activar el reporte de Billing requiere confirmar costo, habilitar exportacion de Cloud Billing y esperar la tabla.
- Conectar Google Sheets requiere spreadsheet ID, worksheet y credenciales del usuario.
- Mapudungun fue cancelado explicitamente por el usuario el 2026-08-09; no se incorporara al selector ni se mantendra como bloqueo.
- No publicar imagen ni desplegar GCE hasta pedido explicito del usuario.

## Siguiente paso exacto

No hay trabajo de codigo local activo. El siguiente paso del usuario es elegir/aprobar los tres artes y aportar sus `file_id` para la prueba local. El proximo release debe incluir la version `0.17` y todas las correcciones acumuladas; usar Bot Control Center, vista Deploy, `Verificar` y `Publicar y deployar`, sin migrar datos locales. Los demas pendientes requieren los datos o autorizaciones explicitados en BACKLOG.
