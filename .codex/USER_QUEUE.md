# Pendientes

- quiero que para este proyecto y todos los que tengan una UI que se use para prender / apagar / configurar procesos, se defina el comportamiento de que el proceso / bot / servidor / lo que sea se cierre al cerrar la UI en lo posible
- LOS TRIGGERS tienen que aceptar cualquier tipo de mensaje que el bot pueda enviar. por ejemplo los stickets, videomensajes, etc. un ejemplo de un mensaje que no puede aceptar es el de que un usuario entró al chat porque no lo puede enviar


# Procesadas

- [2026-07-10] Resolver todo el backlog que no requiera ayuda o inputs y listar al final lo que permanezca pendiente.
- [2026-07-10] Corregir el icono de Windows del panel Galerazo comparandolo con Spider Tracker y borrar `image.png` al terminar.
- [2026-07-10] Mostrar en configuracion una alerta cuando el canal de logging no exista, el bot no sea miembro o no tenga permisos.
- [2026-07-10] Impedir que `/bloquear` bloquee al propio bot y responder `Ni se te ocurra...`.
- [2026-07-10] Hacer que `/debug` devuelva JSON puro sin fences Markdown.
- [2026-07-10] Mostrar nombres sin `@` en todas las listas y agregar `/bloqueados` como alias de `/listanegra`.
- [2026-07-10] Agrupar visualmente `/help` por familias de comandos.
- [2026-07-10] Corregir tildes y usar espanol argentino con voseo en todos los textos.
- [2026-07-10] Agregar `/eliminartrigger` y `/eltrigger` como aliases de borrado.
- [2026-07-10] Permitir nombres de trigger con espacios y longitud de 5 a 32 caracteres.
- [2026-07-10] Permitir dados/emojis animados soportados por Telegram y stickers como respuestas de trigger.
- [2026-07-10] Aceptar `.`, `>`, `$`, `galerazobot` y `galerazo_bot` como prefijos de comandos al inicio.
- [2026-07-10] Implementar `/ruletarusa` persistente, configurable y con las protecciones pedidas para bot, admines y devs.
- [2026-07-10] Revisar y simplificar el proyecto solo donde exista un beneficio claro.
- [2026-07-10] Mantener Python y las librerias en la ultima version estable posible, usando exactamente la misma version en Windows y Docker y haciendo rollback si una actualizacion causa problemas.
- [2026-07-10] Configurar globalmente que, al iniciar una ejecucion por un nuevo mensaje, las tareas pendientes de `USER_QUEUE.md` no solo pasen al backlog sino que se resuelvan automaticamente hasta completarse o quedar realmente bloqueadas; aplicar a proyectos activos y futuros.
- [2026-07-10] Garantizar instancia unica del bot y de los paneles Galerazo/Spider Tracker.
- [2026-07-10] Agrandar visualmente la pestana seleccionada del panel Galerazo.
- [2026-07-10] Revisar logs nuevos mediante checkpoint al finalizar cada instruccion y corregir errores detectados.
- [2026-07-10] Formatear `/help` con `/comando`.
- [2026-07-10] Agregar `/start` con saludo y referencia a `/help`.
- [2026-07-10] Corregir `/debug` con JSON en mensaje o archivo segun limite.
- [2026-07-10] Procesar updates pendientes recibidas mientras el bot estuvo apagado.
- [2026-07-10] Registrar la update que causa cada fallo.
- [2026-07-10] Mostrar el icono del conejo en la barra de tareas del panel.
- [2026-07-10] Corregir la doble respuesta de `/galerazas` y hacer que comandos no implementados se ignoren silenciosamente.
- [2026-07-10] Aplicar la memoria persistente a todos los proyectos activos y futuros sin requerir un pedido adicional.
- [2026-07-10] Crear memoria persistente del proyecto en `.codex/` con contexto, decisiones, backlog, cola del usuario y handoff; exigir actualizacion continua y push al finalizar sesiones.

Para agregar pedidos durante otra sesion, escribirlos en `Pendientes`. El agente debe incorporarlos a `BACKLOG.md` y moverlos a `Procesadas` al comenzar.
