# Retención de imágenes Docker

El repositorio dedicado a `galerazobot` conserva la imagen productiva, la anterior
para rollback y los digests reales de todos los contenedores existentes, incluido
el supervisor del túnel. Google preserva los manifiestos hijos de los índices
retenidos. No se borran indiscriminadamente las imágenes sin etiqueta.

`scripts/registry_retention.py` lee por IAP únicamente `/opt/galerazo/image.env`,
`previous-image.env` y metadatos Docker. Nunca lee el archivo secreto del bot ni
descarga imágenes. La cuenta que ejecuta el release necesita leer imágenes y
actualizar la política del repositorio; no se amplían permisos automáticamente.

Se instalan dos políticas nativas de Artifact Registry:

- `galerazo-keep-required`: conserva los digests protegidos, sin límite de edad.
- `galerazo-delete-obsolete`: elimina versiones del prefijo `galerazobot` con más
  de 24 horas que no estén protegidas. El repositorio es dedicado; no publicar
  otros paquetes que compartan ese prefijo.

La API admite prefijos de versión de hasta 64 caracteres: `sha256:` más los
primeros 57 dígitos hexadecimales del hash validado completo. Una coincidencia
adicional sólo conservaría contenido extra; nunca elimina una imagen protegida.

La imagen candidata se protege **antes** de modificar producción, aunque sea una
imagen publicada hace varios días. Después de un deploy saludable se recalculan
las referencias. Si falla el deploy, la candidata puede quedar conservada hasta
la siguiente sincronización segura; se prioriza la recuperación sobre el ahorro.
Reintentar la misma imagen no reemplaza el verdadero rollback por ella misma.
Un rollback normal intercambia las dos referencias ya protegidas.

La limpieza se ejecuta en segundo plano aproximadamente cada día. Los hijos de
un índice eliminado pueden esperar otro ciclo, y las capas no referenciadas
tienen su propia eliminación diaria. No es un límite instantáneo de 512 MiB:
durante una publicación, con imágenes grandes o con un contenedor que todavía
usa una versión antigua puede ser necesario conservar más de dos imágenes.
Revisar el tamaño informado por Google; no prometer costo cero por esta política.

## Inspección y configuración inicial

Usar el Python de `.venv`. El modo predeterminado sólo genera una propuesta:

```powershell
.venv\Scripts\python.exe scripts\registry_retention.py `
  --project <PROJECT_ID> --zone <ZONE> --instance <INSTANCE> `
  --receipt deploy/out/retention-preview.json
```

Para aplicar una política revisada, añadir `--apply`. Los recibos sólo contienen
referencias de imágenes, metadatos del runtime y políticas; `deploy/out/` está
ignorado por Git. `--location` y `--repository` permiten seleccionar el registro.
No crear APIs, cuentas ni recursos adicionales para ejecutar la herramienta.

`Deploy-Gce.ps1` llama automáticamente a `Sync-GceRegistryRetention.ps1` antes y
después del deploy. Esto no autoriza ejecutar un release: los controles existentes
de publicación, broadcast y autorización de producción siguen siendo obligatorios.
No ejecutar `deploy.sh` directamente saltando la protección previa.

Una referencia vacía, un digest desconocido, un cambio concurrente del runtime o
políticas ajenas bloquean la actualización. Si la verificación final falla, se
pausa la eliminación mediante dry run y se debe investigar antes del siguiente
release. No reintentar un deploy saludable sólo porque falló la retención final;
sincronizar la política por separado después de corregir la causa.

## Validación

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_registry_retention.py
.venv\Scripts\python.exe -m coverage run -m pytest
.venv\Scripts\python.exe -m coverage json
.venv\Scripts\python.exe scripts/check_coverage.py
```

La herramienta forma parte de la cobertura de producción al 100 %. Las pruebas
no acceden a Google ni a Telegram; verifican también cambios concurrentes,
identidades de imágenes en uso, configuración ajena y pausa ante una lectura
final fallida. La configuración real debe confirmar `cleanupPolicyDryRun=false`
y los digests protegidos sin alterar los contenedores.

Referencias: [políticas nativas y protección de manifiestos hijos](https://docs.cloud.google.com/artifact-registry/docs/repositories/cleanup-policy),
[eliminación diaria de capas no referenciadas](https://docs.cloud.google.com/artifact-registry/docs/docker/manage-images#deleting_images).
