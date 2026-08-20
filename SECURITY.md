# Política de seguridad

No publiques tokens, claves, credenciales, archivos `.env`, bases de datos, logs ni identificadores operativos reales en issues, discusiones o pull requests.

Para informar una vulnerabilidad, usa **Security > Report a vulnerability** en GitHub. Incluí una descripción breve, el impacto y los pasos mínimos para reproducirla, sin adjuntar secretos reales. El reporte se mantendrá privado mientras se revisa.

Si una credencial se expone accidentalmente, revocala o rotala de inmediato. Borrar el texto en un commit posterior no la elimina del historial ni invalida la credencial.

Las configuraciones locales deben partir de `.env.example` y guardar sus valores reales solamente en `.env` o en el almacén de secretos del entorno de ejecución.
