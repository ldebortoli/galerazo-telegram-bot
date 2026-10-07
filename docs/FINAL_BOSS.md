# Hisopo Jefe Final

Implementado para la versión 0.72. Su publicación y despliegue requieren el flujo de release habitual; este documento no implica que esté activo en producción.

## Sorteo

La tabla de 10.000 resultados reserva uno al Jefe Final (0,01 %, descontado del Común: 29,64 %). El Gigante ocupa 100 resultados (1 %, descontado del Plateado: 13,25 %). Los demás pesos se conservan y la suma es 100 %.

El Jefe siempre aparece visible como Jefe Final: nunca puede salir de un Misterioso. Su probabilidad total es exactamente 1/10.000 (0,01 %). El Misterioso redistribuye los pesos de los demás tipos sobre 9.299 resultados, excluyendo al propio Misterioso y al Jefe.

## Fases

| Fase | Objetivo | Plazo propio |
| --- | --- | --- |
| 1: cooperación | Misma meta del Gigante: entre 1 y 15 humanos no bots ni cuentas eliminadas; una ayuda por persona. | 60 minutos desde la aparición. |
| 2: frenesí colectivo | 1.000 toques válidos sumados entre todos. Cada cuenta debe espaciar sus toques al menos 100 ms. | 30 minutos desde que superan la fase 1. |
| 3: coordinación | 20 botones, cada uno una sola vez y máximo 5 por persona. Repetir un botón o intentar un sexto provoca derrota. Los botones usados quedan marcados, pero siguen siendo una infracción si alguien los pulsa. | 30 minutos desde que superan la fase 2. |
| 4: acertijo | 20 botones numerados; 19 explotan y uno gana. El acertijo indica un único número: «Mi triple, más siete, da N». | 10 minutos desde que superan la fase 3. |

La fase 3 necesita al menos cuatro personas. La meta no se rebaja en grupos pequeños. Cada fase recibe su plazo completo al empezar; el tiempo sobrante de la anterior no se acumula. Un reinicio conserva el vencimiento absoluto.

El botón seguro se sortea y persiste antes de jugar. Las pistas y los botones no revelan la respuesta directamente. Los callbacks de una fase anterior se descartan y reparan la vista, sin provocar derrota en la fase siguiente. Recibir dos veces el mismo callback tampoco cuenta como dos toques ni como infracción.

## Victoria y puntajes

Al superar las cuatro fases, cada persona con al menos una contribución válida recibe el Jefe en la colección del grupo y:

- 100 puntos base por haber participado en cualquier fase.
- 200 adicionales si ayudó en la fase 1.
- Un punto por cada toque válido aportado en la fase 2.
- 100 puntos por cada botón válido tocado en la fase 3.
- 500 adicionales si acertó el botón de la fase 4.

Todos los puntos y desbloqueos se acreditan en una única transacción al ganar. No se adelantan premios entre fases. La victoria programa la aparición habitual del día siguiente, respetando el límite diario existente.

## Derrotas

| Momento | Resultado |
| --- | --- |
| Fase 1, sin ninguna ayuda | −10 a cada cuenta que figura en la tabla de Hisopos de ese grupo. |
| Fase 1, después de comenzar | −2 a las cuentas de esa tabla que no ayudaron. |
| Fase 2 | Sin puntos ni penalización. |
| Fase 3 | +1 de consuelo a quienes hicieron alguna contribución válida en el evento, excepto quien cometió la infracción. |
| Fase 4 | +2 de consuelo a quienes hicieron alguna contribución válida en el evento, excepto quien hizo explotar el Jefe. |

Los vencimientos en fases 3 y 4 también dan el consuelo correspondiente: no hay infractor que excluir. Ninguna derrota desbloquea el Jefe ni entrega los premios de victoria.

Un mensaje nuevo explica el resultado y los puntos por persona. En fase 3 identifica la regla que causó la derrota y al infractor cuando corresponde. En fase 4 explica la explosión o el vencimiento y muestra el botón correcto con la cuenta que resuelve el acertijo. Nunca revela esa solución si el grupo no llegó a fase 4. Los repartos largos se presentan en un mensaje paginado que también queda excluido del borrado automático.

## Persistencia y Telegram

`final_boss_states` conserva la fase, el botón seguro, el resultado y el anuncio; `final_boss_events` registra callbacks aceptados y rechazados. SQLite serializa las acciones con `BEGIN IMMEDIATE`; ganar, perder y repartir puntos son operaciones idempotentes.

El mensaje de la imagen queda excluido del borrado automático desde su creación, incluso si vence o el grupo pierde. Una victoria reemplaza la foto por la imagen del Jefe derrotado; una derrota muestra al Jefe victorioso con la explicación y sin botones de juego, incluso si venció el tiempo antes de la primera ayuda. El vencimiento del Jefe es automático: no requiere un toque; cada callback también verifica la fecha para rechazar jugadas tardías.

La fase 2 agrupa actualizaciones visuales cada tres segundos para evitar una edición de mensaje por cada toque. Cada callback válido se registra inmediatamente. Las transiciones, derrotas y victoria solicitan actualización inmediata. Una revisión cada minuto recupera resultados pendientes, vistas activas y vencimientos tras errores de envío. Ese trabajo se inicia únicamente cuando aparece un Jefe o se restaura uno activo/con resultado pendiente, y se elimina cuando no queda trabajo del Jefe. Los reinicios conservan la fecha persistida. Los demás Hisopos mantienen su comportamiento anterior de vencimiento.

El anuncio persiste el identificador confirmado antes de montar su paginación. Si falla ese montaje, se repara el mismo mensaje. Telegram no ofrece una clave idempotente para `sendMessage`: un corte exacto entre la confirmación remota y su registro local puede duplicar un aviso, pero nunca duplica puntos ni desbloqueos.

Desde 0.73, el bot usa seis `file_id` configurados manualmente; nunca sube de nuevo las imágenes durante la batalla. Se obtienen enviando o reenviando cada foto al mismo bot que jugará el evento y consultando su `file_id` con `/debug` (no `file_unique_id`). Telegram asigna referencias por bot: las del bot de prueba no sirven para Galerazo Bot.

```dotenv
TELEGRAM_HISOPO_FINAL_BOSS_PHASE_1_FILE_ID=
TELEGRAM_HISOPO_FINAL_BOSS_PHASE_2_FILE_ID=
TELEGRAM_HISOPO_FINAL_BOSS_PHASE_3_FILE_ID=
TELEGRAM_HISOPO_FINAL_BOSS_PHASE_4_FILE_ID=
TELEGRAM_HISOPO_FINAL_BOSS_DEFEATED_FILE_ID=
TELEGRAM_HISOPO_FINAL_BOSS_VICTORIOUS_FILE_ID=
```

Si falta alguna de las seis referencias, el sorteo usa un Común en lugar de iniciar un Jefe incompleto. Cambiar una ilustración requiere reemplazar su referencia manualmente. Los archivos fuente se conservan en `assets/hisopos/`. La Mini App ya incorpora el Jefe bloqueado, conseguido y en álbumes compartidos; usa el arte derrotado y el nombre localizado enviados por la API. Prompts y revisión visual: [FINAL_BOSS_ART_PROMPTS.md](FINAL_BOSS_ART_PROMPTS.md).

## Validación local

```powershell
.venv\Scripts\python.exe -m pytest tests/test_final_boss.py tests/test_final_boss_telegram.py tests/test_final_boss_integration.py tests/test_final_boss_translations.py
.venv\Scripts\python.exe -m coverage run -m pytest
.venv\Scripts\python.exe -m coverage json
.venv\Scripts\python.exe scripts/check_coverage.py
```

La integración juega una victoria completa con 1.000 contribuciones reales. Los casos adicionales del motor conservan toques reales y casos de límite, con datos intermedios sembrados para no repetir cientos de sincronizaciones de disco por escenario. La suite cubre transacciones, duplicados, concurrencia, reinicio, plazos, premios, consuelos, exclusión del infractor, mensajes y recuperación.
