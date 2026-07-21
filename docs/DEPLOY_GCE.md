# Deploy de Galerazobot en Google Compute Engine

## Diseño elegido

```text
PC local o GitHub Actions
        |
        | construye linux/amd64
        v
Google Artifact Registry
        |
        | pull autenticado
        v
GCE e2-micro + Docker Compose
        |
        +-- /srv/galerazo/data       SQLite persistente
        +-- /srv/galerazo/backups    backups previos a deploy
        +-- /etc/galerazo/bot.env    secretos, fuera de Git
```

No hay webhook ni puerto de aplicacion. SSH entra mediante IAP y no requiere una
IPv4 publica. El flujo normal se ejecuta desde la PC para conservar una
confirmacion humana antes de tocar produccion.

## Que se configura una vez y que se repite

| Alcance | Configuracion |
| --- | --- |
| Una vez por proyecto de flota | Proyecto, facturacion, presupuesto, APIs y repositorio `bots`. |
| Una vez por bot | Service account, VM, secretos, directorios persistentes y primer deploy. |
| Por release | Tests, build, publicacion de una imagen inmutable y deploy con healthcheck. |

Los pasos tecnicos validados de APIs, Artifact Registry e identidad se pueden
repetir de forma segura con:

```powershell
.\scripts\deploy\Initialize-GcpBot.ps1 `
  -ProjectId bot-fleet-production `
  -ServiceAccountId galerazo-vm `
  -ServiceAccountDisplayName "Galerazo production VM"
```

El script es idempotente: comprueba el estado antes de crear, limita Reader y
Writer al repositorio `bots`, verifica que la identidad no tenga claves
administradas por el usuario y no crea ninguna VM. Para otro bot se reutilizan
el proyecto y el registro, cambiando `ServiceAccountId` y el nombre visible.
La vinculacion inicial de facturacion y el presupuesto se conservan como pasos
explicitos porque dependen del titular y de la politica de costos de la cuenta.

### Runbook reproducible de punta a punta

Los unicos pasos deliberadamente manuales son los que requieren aceptar
condiciones/costos o entregar secretos:

1. **Manual, una vez por cuenta:** crear/iniciar la cuenta de Google, activar la
   prueba o facturacion, aceptar sus condiciones y elegir el medio de pago.
2. **Manual asistido, una vez por proyecto:** iniciar sesion con `gcloud auth
   login`, elegir un Project ID globalmente unico, vincular la cuenta de
   facturacion y crear el presupuesto/alertas. Si se usan comandos:

   ```powershell
   gcloud projects create TU_PROYECTO --name="Bot Hosting Production"
   gcloud billing projects link TU_PROYECTO --billing-account=TU_BILLING_ACCOUNT
   gcloud config set project TU_PROYECTO
   ```

   El presupuesto recomendado es USD 1 mensual, incluye Free Tier y otros
   ahorros, excluye promociones, y alerta gasto real al 10/50/100% mas
   pronostico al 100%. Confirmar tambien que la cuenta de facturacion no consume
   ya las horas/disco gratuitos en otro proyecto.
3. **Automatizado:** preparar APIs, registro, identidad, red, IAP, VM y host:

   ```powershell
   .\scripts\deploy\Invoke-GceBotLifecycle.ps1 `
     -Action Prepare `
     -ProjectId TU_PROYECTO `
     -AcknowledgeBillableResource
   ```

4. **Manual y secreto, una vez por bot:** completar
   `/etc/galerazo/bot.env`; apagar el proceso local que usa el mismo token; crear
   una copia consistente de SQLite y subirla a
   `/srv/galerazo/data/galerazo.sqlite3`. Las instrucciones exactas estan en la
   seccion de migracion de esta guia.
5. **Automatizado:** probar, construir, publicar y desplegar la release:

   ```powershell
   .\scripts\deploy\Invoke-GceBotLifecycle.ps1 `
     -Action Release `
     -ProjectId TU_PROYECTO `
     -AcknowledgeProductionDeploy
   ```

6. **Releases futuras:** repetir solo el comando `Release`. Para volver a la
   imagen anterior usar `-Action Rollback -AcknowledgeProductionDeploy`.

El orquestador tambien permite ejecutar cada bloque de forma independiente con
`Foundation`, `Infrastructure`, `Prepare`, `Publish`, `Deploy`, `Release` o
`Rollback`. Antes de desplegar, verifica que el bot local este apagado, que los
secretos/base remotos existan y que la imagen tenga un tag inmutable distinto
de `latest`. Esto permite que Bot Control Center invoque `Release` mas adelante
sin duplicar la logica de deploy.

## Costos y minutos de CI

La imagen no necesita generarse en GitHub. El camino local usa Docker Desktop y
publica desde la PC, por lo que consume cero minutos de Actions. GitHub Free
incluye actualmente 2.000 minutos mensuales para repositorios privados, pero la
publicacion remota queda manual para reservarlos para tests y releases elegidas.

Artifact Registry no cobra los primeros 0,5 GB almacenados y luego cobra por
GB-mes. Conservar pocas etiquetas y eliminar releases obsoletas evita acumular
almacenamiento. No usar `latest`: cada imagen se etiqueta con el commit o un tag
inmutable y asi el rollback es determinista.

## 1. Requisitos en la PC

Instalar:

1. Docker Desktop configurado para contenedores Linux.
2. Google Cloud CLI (`gcloud`).
3. Una cuenta autenticada:

```powershell
gcloud auth login
gcloud config set project TU_PROYECTO
```

Los scripts verifican estos comandos y fallan antes de modificar estado si falta
alguno. No instalan Docker Desktop ni `gcloud` automaticamente.

En Windows se recomienda Docker Desktop por usuario con backend WSL 2 y
contenedores Linux. Google Cloud CLI debe autenticarse con `gcloud auth login`
y usar el proyecto de la flota como `core/project`; no hace falta guardar una
clave JSON local para estas operaciones interactivas.

## 2. Crear el proyecto y el registro

Para una flota personal de bots conviene usar un proyecto GCP generico y
compartido, con nombres, service accounts, directorios y datos separados por
bot. Reservar un proyecto por bot para clientes, responsables de pago o
permisos que necesiten aislamiento fuerte. El proyecto necesita facturacion
habilitada aunque el uso quede dentro del Free Tier.

Antes de crear recursos, configurar un presupuesto mensual de USD 1 sobre la
cuenta o el proyecto correspondiente. Incluir los creditos de Free Tier,
excluir los creditos promocionales y alertar por gasto real al 10%, 50% y 100%,
mas gasto previsto al 100%. Esto permite ver el costo que persistiria despues
de la prueba gratuita. El presupuesto solo alerta: no limita el consumo ni
detiene recursos, y sus datos pueden llegar con demora.

La ruta recomendada usa el script idempotente mostrado arriba. Como referencia,
el equivalente manual para la identidad de la VM debe limitar el permiso al
repositorio, no a todo el proyecto:

```powershell
gcloud iam service-accounts create galerazo-vm `
  --display-name="Galerazo production VM"

gcloud artifacts repositories add-iam-policy-binding bots `
  --location=us-central1 `
  --member="serviceAccount:galerazo-vm@TU_PROYECTO.iam.gserviceaccount.com" `
  --role="roles/artifactregistry.reader"
```

La cuenta humana que publique localmente necesita
`roles/artifactregistry.writer` sobre el repositorio. El script lo concede a la
cuenta activa de `gcloud` sin crear ni descargar claves JSON.

## 3. Crear la VM elegible para Free Tier

En Compute Engine crear `galerazo-prod` con:

- region `us-central1`, `us-east1` o `us-west1`;
- tipo `e2-micro`, no Spot;
- Ubuntu 24.04 LTS o Debian estable;
- disco `pd-standard` de hasta 30 GB;
- service account `galerazo-vm` y scope `cloud-platform`;
- Shielded VM habilitada;
- sin IPv4 externa;
- interfaz dual-stack con IPv6 externa en una subnet que tenga IPv6 externo;
- ninguna regla publica para Docker o la aplicacion.

La configuracion dual-stack se hace en **Networking > Network interfaces**:
seleccionar una subnet con rango IPv6 externo, `IPv4 and IPv6`, External IPv4
`None` y External IPv6 `Ephemeral`. Si la VPC por defecto aun es solo IPv4,
primero hay que convertir o crear una subnet dual-stack siguiendo la guia
oficial de IPv6 de Compute Engine.

Para IAP, permitir TCP 22 desde `35.235.240.0/20` y conceder al usuario que
administra la VM los roles de IAP tunnel y login/OS Login correspondientes. IAP
autentica el acceso aunque la VM no tenga una IP publica IPv4.

Antes de continuar, verificar:

```powershell
gcloud compute ssh galerazo-prod `
  --project TU_PROYECTO `
  --zone us-central1-a `
  --tunnel-through-iap
```

La VM necesita salida IPv6 funcional para descargar paquetes, consultar
Telegram y descargar imagenes. Si una dependencia concreta no soporta IPv6,
detener el setup y decidir entre Cloud NAT o una IPv4 externa; ambos pueden
agregar costo.

## 4. Instalar Docker y preparar directorios

Desde el root del repositorio:

```powershell
.\scripts\deploy\Initialize-GceHost.ps1 `
  -ProjectId TU_PROYECTO `
  -Zone us-central1-a `
  -Instance galerazo-prod
```

El bootstrap instala Docker Engine, Compose y Google Cloud CLI desde los
repositorios oficiales. Luego crea estas rutas protegidas:

- `/opt/galerazo`: Compose y scripts de deploy;
- `/srv/galerazo/data`: base persistente, UID/GID 10001;
- `/srv/galerazo/backups`: backups persistentes;
- `/etc/galerazo/bot.env`: variables secretas, modo `0600`;
- `/etc/galerazo/secrets`: credenciales opcionales, modo `0700`.

Al final ejecuta `deploy/gce/verify-host.sh` para comprobar versiones, servicio
Docker y permisos sin imprimir secretos. Tambien se puede ejecutar manualmente
con `--expect-pristine` antes de cargar datos para exigir que no haya imagenes,
contenedores ni base remota.

### Checklist visual en Google Cloud Console

Despues de `Prepare`, revisar estas pantallas. El bootstrap no debe crear
recursos nuevos en Google Cloud: solo instala software y crea archivos dentro
de la VM.

- **Compute Engine > Instancias de VM:** `galerazo-prod` debe estar `RUNNING`,
  en `us-central1-a`, como `e2-micro`, sin IPv4 externa y con IPv6 externa
  efimera. En sus detalles deben figurar `galerazo-vm`, OS Login, Shielded VM,
  deletion protection y el tag `iap-ssh`.
- **Compute Engine > Discos:** un unico disco de arranque de 30 GB,
  `pd-standard`, en `us-central1-a` y conectado a `galerazo-prod`.
- **Red de VPC > Redes de VPC:** `bot-fleet` en modo custom y la subred
  `bots-us-central1` (`10.20.0.0/24`), dual-stack, IPv6 externo y Private Google
  Access habilitado.
- **Red de VPC > Firewall:** para `bot-fleet`, la regla propia esperada es
  `bot-fleet-allow-iap-ssh`: entrada TCP 22 desde `35.235.240.0/20`, dirigida al
  tag `iap-ssh`. No debe existir una regla que publique SSH al mundo ni puertos
  de la aplicacion.
- **Artifact Registry > Repositorios:** `bots`, formato Docker y region
  `us-central1`. Antes de `Publish` debe seguir sin imagenes.
- **IAM y administracion > Cuentas de servicio:** `galerazo-vm` habilitada y
  con cero claves administradas por el usuario.
- **Facturacion > Presupuestos y alertas:** el presupuesto mensual debe estar
  activo. Es una alerta, no un corte; el costo puede aparecer con varias horas
  de demora.

La pestaña **Observabilidad** de la VM permite revisar CPU, red y disco. La RAM
no aparece en Cloud Monitoring sin instalar el Ops Agent; no se instala en este
setup para evitar carga adicional innecesaria en la `e2-micro`.

Entrar por IAP y completar los secretos manualmente:

```bash
sudo nano /etc/galerazo/bot.env
```

Nunca pasar el token como argumento de `gcloud`, subir `.env` ni guardarlo en
GitHub. Para Google Sheets, copiar el JSON a
`/etc/galerazo/secrets/google-service-account.json` y configurar dentro de
`bot.env`:

```env
GOOGLE_SHEETS_CREDENTIALS_JSON_PATH=/app/secrets/google-service-account.json
```

## 5A. Construir y publicar desde la PC — recomendado

Construir la imagen y ejecutar las pruebas dentro del target Docker:

```powershell
.\scripts\deploy\Build-DockerImage.ps1
```

Publicarla en Artifact Registry, volviendo a usar el commit como tag:

```powershell
.\scripts\deploy\Publish-DockerImage.ps1 `
  -ProjectId TU_PROYECTO `
  -Location us-central1 `
  -Repository bots
```

El script muestra la referencia completa y también la guarda localmente en
`deploy/out/last-image.txt`, archivo ignorado por Git. Para reutilizar una
imagen ya construida se puede pasar `-SkipBuild`.

## 5B. Publicar manualmente desde GitHub

El workflow `.github/workflows/publish-gce-image.yml` solo admite ejecución
manual desde `main` y construye exclusivamente el target de produccion. Antes,
configurar estas **Repository variables**:

```text
GCP_PROJECT_ID
GCP_ARTIFACT_REGISTRY_LOCATION        us-central1
GCP_ARTIFACT_REGISTRY_REPOSITORY      bots
GCP_WORKLOAD_IDENTITY_PROVIDER
GCP_DEPLOY_SERVICE_ACCOUNT
```

`GCP_DEPLOY_SERVICE_ACCOUNT` necesita Artifact Registry Writer. Configurar
Workload Identity Federation para que GitHub use OIDC; no crear ni guardar una
service account key JSON.

En GitHub: **Actions > Publish GCE image > Run workflow**. Dejar `tag` vacio
para usar los primeros 12 caracteres del commit. El resumen del job entrega la
referencia que hay que pasar al deploy local.

Este workflow no despliega la VM y no se ejecuta por push. La publicacion y el
deploy quedan separados para que construir una imagen nunca cambie produccion
por accidente.

## 6. Primer deploy y actualizaciones

Tomar la imagen mostrada por el publicador local o GitHub:

```powershell
.\scripts\deploy\Deploy-Gce.ps1 `
  -ProjectId TU_PROYECTO `
  -Zone us-central1-a `
  -Instance galerazo-prod `
  -Image us-central1-docker.pkg.dev/TU_PROYECTO/bots/galerazobot:COMMIT
```

El deploy remoto:

1. valida que el token no conserve el placeholder;
2. registra la imagen anterior;
3. crea un backup SQLite consistente si hay un contenedor activo;
4. descarga la imagen nueva antes de detener el bot;
5. recrea el contenedor y espera hasta 120 segundos por su healthcheck;
6. restaura automaticamente la imagen anterior si no queda healthy.

El bot usa `drop_pending_updates=False`; durante los pocos segundos de recreacion
Telegram conserva las updates que todavia no hayan expirado.

## 7. Comprobaciones y rollback

```powershell
gcloud compute ssh galerazo-prod `
  --project TU_PROYECTO `
  --zone us-central1-a `
  --tunnel-through-iap `
  --command "sudo docker compose --env-file /opt/galerazo/image.env -f /opt/galerazo/compose.yaml ps"
```

Logs recientes:

```powershell
gcloud compute ssh galerazo-prod `
  --project TU_PROYECTO `
  --zone us-central1-a `
  --tunnel-through-iap `
  --command "sudo docker compose --env-file /opt/galerazo/image.env -f /opt/galerazo/compose.yaml logs --tail 100 bot"
```

Rollback manual a la version registrada anteriormente:

```powershell
.\scripts\deploy\Rollback-Gce.ps1 `
  -ProjectId TU_PROYECTO `
  -Zone us-central1-a `
  -Instance galerazo-prod
```

## 8. Migrar la base local existente

No arrancar local y remoto simultaneamente con el mismo token. Para migrar:

1. apagar Galerazobot desde el panel local;
2. crear un backup consistente con `/backup` o la API local de backup;
3. copiar ese archivo por `gcloud compute scp --tunnel-through-iap`;
4. instalarlo como `/srv/galerazo/data/galerazo.sqlite3` con owner
   `10001:10001` y modo `0600`;
5. hacer el primer deploy;
6. verificar `/hola`, `/nivel`, `/debug` y `/backup`;
7. dejar apagada la instancia local mientras produccion use ese token.

No copiar directamente los archivos `-wal`/`-shm` de una base activa.

Una vez elegido un backup consistente y con el bot local apagado:

```powershell
$backup = "C:\ruta\al\backup-consistente.sqlite3"

gcloud compute scp $backup `
  galerazo-prod:/tmp/galerazo.sqlite3 `
  --project TU_PROYECTO `
  --zone us-central1-a `
  --tunnel-through-iap

gcloud compute ssh galerazo-prod `
  --project TU_PROYECTO `
  --zone us-central1-a `
  --tunnel-through-iap `
  --command "sudo install -o 10001 -g 10001 -m 0600 /tmp/galerazo.sqlite3 /srv/galerazo/data/galerazo.sqlite3 && rm -f /tmp/galerazo.sqlite3"
```

No poner tokens, claves ni contenido de `bot.env` en los argumentos de estos
comandos.

## 9. Operacion segura

- Mantener presupuestos y alertas del proyecto, aun dentro del Free Tier.
- Conservar al menos el backup previo y la imagen anterior.
- Limpiar tags viejos de Artifact Registry despues de verificar una release.
- No agregar puertos al Compose ni montar `/var/run/docker.sock`.
- No ejecutar dos replicas: polling y SQLite estan preparados para una sola.
- En `e2-micro`, moderar un video por vez hasta medir el pico real de PyAV.
- Probar un rollback voluntario antes de considerar automatico el deploy.

## Referencias oficiales

- [Free Tier de Google Cloud](https://docs.cloud.google.com/free/docs/free-cloud-features)
- [IAP TCP forwarding](https://docs.cloud.google.com/iap/docs/tcp-forwarding-overview)
- [Instancias IPv6](https://docs.cloud.google.com/compute/docs/instances/create-ipv6-instance)
- [Artifact Registry: push y pull](https://docs.cloud.google.com/artifact-registry/docs/docker/pushing-and-pulling)
- [Observar y supervisar VM](https://docs.cloud.google.com/compute/docs/instances/observe-monitor-vms)
- [Presupuestos y alertas de Cloud Billing](https://docs.cloud.google.com/billing/docs/how-to/budgets)
- [Workload Identity Federation para pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
- [Docker Compose en produccion](https://docs.docker.com/compose/how-tos/production/)
- [Facturacion de GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
