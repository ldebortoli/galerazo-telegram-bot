# Limite mensual de transferencia de la Mini App

Implementado desde 0.62 y activado en produccion el 2026-09-07 con el release
autorizado. El corte de 950 MB requiere 0.63; hasta desplegar esa correccion,
0.62 mantiene el corte de 925 MB. Las instalaciones adicionales requieren configurar la Mini App.
El supervisor corre en la VM existente, sin servicios pagos de Monitoring,
BigQuery ni otra VM. Las imagenes ya se sirven comprimidas desde Cloudflare.

## Contrato de funcionamiento

| Salida contabilizada de la VM | Accion |
| --- | --- |
| 700 MB | Aviso en el chat de logging configurado |
| 850 MB | Segundo aviso |
| 950 MB o mas | Detener cloudflared y avisar; mantener Telegram activo |
| Dia 1, 08:00 UTC | Nuevo periodo; permitir el tunel si el contador es fiable |
| Lectura/persistencia fallida o historial incompleto | Mantener el tunel cerrado |

MB significa 1.000.000 bytes; el corte es **950.000.000 bytes**, conservador
frente a 1 GB/GiB. Se muestrea cada 2 segundos, con hasta 1 segundo adicional
para detener el proceso antes de forzar su salida. El supervisor posee el
proceso cloudflared; al morir su contenedor no sobrevive un tunel independiente.
Un aviso lento no bloquea el muestreo. Se consolidan umbrales saltados en un
solo aviso del nivel alcanzado; un aviso fallido reintenta cada 10 minutos y
un nivel nuevo puede avisar antes. Los avisos confirmados se guardan en disco.
Un crash despues de enviar pero antes de guardar puede duplicar un aviso.

Se suman `tx_bytes` de todas las interfaces fisicas: incluye Telegram, tunel,
TLS, ACK, mantenimiento y salida no facturable; excluye loopback y veth para
no contar el mismo paquete dos veces. **No es el medidor de facturacion** ni
incluye otras VM/proyectos que compartan el cupo de la cuenta. Al cortar solo
la Mini App, Telegram y el sistema operativo siguen generando salida. Los
paquetes en vuelo y el intervalo de medicion pueden sobrepasar el umbral.
No promete una factura de cero ni un tope de centavos para toda la cuenta.

Google documenta la agregacion mensual por SKU desde el dia 1 a medianoche
Pacific UTC-8. Usamos UTC-8 fijo (08:00 UTC, 05:00 Argentina); no adelantamos
el reinicio durante el horario de verano. La muestra que cruza el mes se
imputa completa al nuevo mes para no omitir bytes del intervalo.

## Persistencia y primer mes

`/srv/galerazo/traffic/budget.json` guarda mes, bytes acumulados, ultimo contador,
identidad de arranque/interfaz y aviso confirmado. Escritura temporal + fsync +
reemplazo atomico; no se monta la base del bot. Un reinicio del supervisor suma
la diferencia del contador aunque haya estado apagado.

Sin archivo valido, solo se permite abrir si la VM estaba encendida desde
antes de empezar el mes: se cuenta **toda** su salida desde ese arranque como
estimacion superior, incluyendo meses anteriores. Si arranco este mes, falta
el historial anterior y se mantiene pausada. Una caida de contador, cambio de
interfaz o reinicio de VM deja el periodo bloqueado. El siguiente mes puede
recuperarse con mediciones continuas. No borrar ni editar el archivo para
reabrir la Mini App y no inicializar artificialmente el contador en cero.

En la inspeccion del 2026-09-07, el contador de unos 805 MB incluia trafico
desde julio. Monitoring registra aproximadamente 130 MB del 1 al 7 de septiembre,
con dos intervalos de un minuto sin datos. Para corregir ese primer mes se
aplico una base estimada de 150 MB, que incluye unos 20 MB de reserva, mas
todo el trafico local posterior a una muestra de enlace. Esa reserva es una
precaucion operativa, no una cota demostrada de los minutos sin datos ni una
garantia de facturacion. No se instalan agentes ni metricas personalizadas.
La correccion se aplico a las 22:15 UTC con copia previa: 150.135.974 bytes
incluyendo el trafico desde la muestra de enlace. El supervisor confirmo despues
150.200.355 bytes, mes 2026-09 y aviso actualizado; el bot permanecio saludable.

### Correccion auditada de una base mensual

1. Leer la metrica nativa `compute.googleapis.com/instance/network/sent_bytes_count`
   mediante `projects.timeSeries.list`, filtrando proyecto, instancia y mes
   calendario. Sumar los DELTA en bytes, revisar paginacion, intervalos y huecos.
   Conservar privadamente la respuesta original y la estimacion/reserva elegida.
2. Capturar una muestra local `anchor`. Esperar a que Monitoring cubra al menos
   esa fecha (ingesta hasta 240 segundos) y comprobar que la base elegida cubre
   el total observado hasta esa muestra mas la reserva declarada.
3. Detener **solo** el supervisor, respaldar el estado previo y obtener una
   muestra `current`. Calcular `monthly_baseline(period, used, anchor, current)`:
   exige el mismo mes, arranque e interfaces y contadores monotones; suma el
   trafico transcurrido desde `anchor`. Si alguna comprobacion falla, abortar.
4. Guardar atomicamente el nuevo presupuesto, conservar UID/GID 10001 y permisos
   privados, arrancar el supervisor y verificar incremento del contador, tunel y
   bot saludable. El siguiente muestreo suma tambien los bytes de la operacion.

La correccion es una operacion administrativa puntual. No consulta APIs cada
mes: desde entonces el supervisor conserva muestras continuas y abre un nuevo
periodo el dia 1, sin llevar el saldo anterior. Un reinicio del proceso dentro
del mismo mes conserva el saldo. No convertir una caida de contador en un reset.

## Activacion en el release autorizado

1. Completar [la integracion](MINIAPP_INTEGRATION.md), verificar el margen y
   aprobar/publicar el release por el flujo existente. No usar una imagen
   anterior a 0.62. La unidad usa la imagen ya instalada de
   `/opt/galerazo/image.env` con `--pull=never`; no publica ni descarga imagenes.
2. Instalar una version estable verificada del binario Linux estatico de
   cloudflared en `/usr/bin/cloudflared`, root:root 0755. Verificar que se ejecuta
   en la imagen aprobada. No instalar un segundo servicio cloudflared que eluda
   al supervisor. Conservar version/checksum en el registro de operacion.
3. Preparar el directorio de estado con propietario UID:GID `10001:10001` y modo
   0700. Guardar `/etc/galerazo/cloudflared.token` como `10001:10001`, modo 0400.
   El token se monta como archivo, nunca se pasa como argumento.
4. Crear privadamente `/etc/galerazo/traffic-notifications.env`, root:root 0600,
   con **solo** `TELEGRAM_BOT_TOKEN` y `TELEGRAM_LOG_CHAT_ID`, tomados del bot
   productivo y su chat de logging ya configurado. No imprimirlos, incluirlos
   en Git, comandos o la imagen. Docker los carga en el supervisor; el hijo
   cloudflared recibe un entorno limpio sin el token de Telegram.
5. Instalar `deploy/gce/miniapp-tunnel.service` como
   `/etc/systemd/system/galerazo-miniapp-tunnel.service`, root:root 0644.
   Ejecutar `systemd-analyze verify` sobre la unidad, `systemctl daemon-reload`
   y `systemctl enable --now galerazo-miniapp-tunnel.service` durante el corte.
6. Comprobar estado JSON y journal, recepcion del aviso inicial en Logs y que
   existe solo el tunel supervisado. Si el primer muestreo supera el limite o
   no hay historial fiable, **la pausa es el resultado esperado**.

El servicio corre un contenedor separado, no root, sin capacidades, puertos,
Docker socket, SQLite ni el entorno completo del bot. Tiene memoria limitada a
128 MB y logs rotados hasta 4 MB. Si el supervisor falla repetidamente, systemd
lo deja detenido tras tres intentos en cinco minutos. La Mini App permanece
cerrada y el fallo queda en el journal; si Telegram falla, no puede garantizar
la entrega del aviso. Investigar y reparar, nunca arrancar cloudflared a mano.

La web y las imagenes estaticas permanecen accesibles al cortar. Las consultas
de album y nuevas facturas fallan temporalmente sin llegar a la VM. Los pagos
ya emitidos siguen siendo recibidos/procesados por el bot de Telegram.
El supervisor no maneja pagos, saldos ni suscripciones.

Para detenerlo: `systemctl stop galerazo-miniapp-tunnel.service`; detiene el
contenedor y el tunel, conservando el contador. Un reinicio normal usa
`systemctl restart galerazo-miniapp-tunnel.service`. Tras cambiar la imagen
del bot, reiniciar esta unidad solo dentro del release coordinado para usar
el mismo runtime. No existe una orden para anular el limite automaticamente.

## Validacion

Suite nativa: `.venv/Scripts/python.exe -m pytest tests/test_traffic_guard.py`.
Prueba umbrales exactos, reinicio y perdida/corrupcion de estado, cambio de mes,
correccion mensual con trafico posterior y rechazo de muestras incompatibles,
reinicio de VM, fallo de disco, perdida de interfaz, HTTP fallido, avisos lentos,
proceso que ignora SIGTERM y salida segura. Las pruebas usan procesos/notificaciones
simulados; el smoke Docker verifica el runtime Linux y un proceso real local sin
conectarse a Telegram ni Cloudflare. El QA autenticado del tunel queda para su
activacion: no se simula exito de una integracion que aun no esta configurada.

Fuentes: [agregacion mensual de Cloud Billing](https://docs.cloud.google.com/billing/docs/how-to/pricing-table#about_pricing_tiers),
[Free Tier Compute Engine](https://docs.cloud.google.com/free/docs/free-cloud-features#compute),
[parametros de cloudflared](https://developers.cloudflare.com/tunnel/advanced/run-parameters/).
