# Session handoff

## Objetivo general

Mantener Galerazo Bot reproducible en Windows, CI y Docker, con SQLite persistente y deploy seguro de bajo costo.

## Estado actual

- No hay tarea local activa. La suite usa `pytest==9.1.1` como runner oficial y `pytest-asyncio==1.4.0` en modo automatico. Conserva los tests heredados `unittest` e `IsolatedAsyncioTestCase`; setup Windows, Docker y CI ya ejecutan `python -m pytest`. Implementado en `6c35090` y pusheado a `main`; no requiere release ni deploy.
- La migracion grupo-supergrupo usa un `MessageHandler(filters.StatusUpdate.MIGRATE)` dedicado en el grupo 0 antes del preprocesador. SQLite reclama una vez la pareja de IDs y los migradores por dominio se ejecutan dentro de esa misma transaccion; el segundo evento de Telegram no modifica datos. Implementado en `209893d` y pusheado a `main`, sin release ni deploy.
- Se incorporaron catálogos completos estáticos para español de España, ruso, latín, japonés, italiano, francés, alemán, holandés, chino simplificado/tradicional, portugués de Brasil/Portugal, catalán, vasco y guaraní. Los comandos conservan sus nombres originales. Versión `0.10`; sin deploy solicitado.
- `USER_QUEUE.md` usa una unica seccion `Procesadas` para el historial y `Pendientes` para pedidos nuevos; se consolidaron las entradas historicas, incluido el `TimedOut` de `/triggers` y el formato de su lista, implementados desde `3fb6048`.
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

- Versión `0.10`: 234 pruebas nativas OK; cobertura 100% de sentencias y ramas; `compileall`, `runtime_versions.py`, `pip check`, `git diff --check` y checkpoint de logs OK. Sin release/deploy.
- 231 pruebas nativas OK; cobertura 100% de sentencias y ramas.
- Target Docker de tests: 224 pruebas OK, una prueba Tk omitida en Linux; runtime Docker de Python 3.14.6 validado.
- `scripts/runtime_versions.py`, `pip check`, `compileall` y `git diff --check` OK.

## Pendientes y bloqueos

- Activar el reporte de Billing requiere confirmar costo, habilitar exportacion de Cloud Billing y esperar la tabla.
- Conectar Google Sheets requiere spreadsheet ID, worksheet y credenciales del usuario.
- Mapudungun estándar requiere una fuente lingüística completa y revisable. Google no ofrece `arn`; los modelos alternativos requieren varios GB e intervención humana. No incluir un catálogo no verificado.
- No publicar imagen ni desplegar GCE hasta pedido explicito del usuario.

## Siguiente paso exacto

No hay trabajo local activo. Ante un pedido posterior de release, construir/publicar una imagen inmutable y desplegarla con el flujo GCE; no migrar datos locales. Los únicos pendientes requieren los datos o autorizaciones explicitados en BACKLOG, incluido un catálogo estándar de Mapudungun revisable.
