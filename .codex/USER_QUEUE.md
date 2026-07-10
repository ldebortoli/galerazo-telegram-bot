# Pendientes

No hay pedidos sin procesar.

# Procesadas

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
