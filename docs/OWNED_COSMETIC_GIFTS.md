# Regalar un cosmético de la colección

En el álbum propio de la Mini App, cada cosmético disponible ofrece **Regalar de mi
colección**. La confirmación explica que se descuenta una unidad, permite ingresar
un alias conocido por el bot o un user ID y entrega esa unidad sin abrir un pago.
La tienda conserva su regalo mediante compra con Stars. Los cosméticos son globales;
los Hisopos naturales, los puntos y la membresía del Club no se transfieren.

`/regalarhisopo` conserva íntegramente su contrato: comando oculto de desarrollo,
sólo por privado, que acredita unidades nuevas. Esta entrega no cambia comandos,
permisos, ayuda ni BotFather.

## Contrato y consistencia

- `POST /api/gift` exige el proxy privado y una firma Telegram vigente. El único
  cuerpo permitido contiene `item_key`, `recipient` y `request_id`. La identidad
  del remitente siempre proviene de Telegram; no se aceptan precio ni cantidad.
- El gateway traduce únicamente el alias editorial Mosquito a la clave de inventario
  existente. No modifica la firma, los usuarios ni los saldos.
- Cada intento utiliza una clave aleatoria persistida con el remitente. Repetir el
  mismo destinatario/artículo devuelve el resultado confirmado; reutilizar esa clave
  con otra operación falla. Un timeout conserva la clave para reintentar sin duplicar.
- El destinatario debe tener una marca de tipo de cuenta recibida de Telegram y
  registrada como no-bot. Bots y registros viejos/desconocidos se rechazan sin
  descuento; el destinatario puede usar el bot o abrir su Mini App para actualizar
  esa marca. No se deduce el tipo por el sufijo del alias ni se presume que un ID
  desconocido sea una persona. La firma de la Mini App rechaza usuarios marcados
  como bots. La comprobación usa datos observados, sin certificar existencia o alias
  actuales mediante una consulta externa.
- Una transacción SQLite inmediata valida disponibilidad y límite int64, mueve una
  unidad y guarda su recibo. No se permite autorregalo, remitente bloqueado ni la
  colección virtual del propio bot. Una colección compartida no muestra acciones.
- Los lotes agregados conservan la procedencia de cada compra o premio del Club.
  Un reembolso revoca la unidad en su dueño actual, incluso tras sucesivos regalos;
  un premio del Club regalado no vuelve a acreditarse. Los regalos independientes
  y los cosméticos heredados conservan su procedencia separada.
- La migración inicial mantiene cantidades y fechas existentes. No enumera unidades
  individuales, de modo que también admite inventarios heredados de tamaño int64.

La respuesta propia de bootstrap incluye `owned_gifts: true`. El frontend oculta la
acción si ese indicador falta, por lo que puede publicarse antes del backend. El
contrato del frontend declara `owned-cosmetic-gifts`; el puente exige esa capacidad
para un bot desde 0.81 y conserva compatibilidad con versiones anteriores.

Los diez textos nuevos están en los 192 catálogos de la Mini App, adquiridos como
traducción automática estática y sin datos de usuarios. No se certifica revisión
lingüística nativa. Los 139 idiomas del bot conservan respuestas y comandos; el
resumen editorial del anuncio conserva el idioma de su texto aprobado, según la
convención documentada en [PRIVATE_LANGUAGES.md](PRIVATE_LANGUAGES.md).

## Validación y recuperación

`tests/test_cosmetic_transfers.py` prueba cantidades, reinicios, reintentos,
concurrencia, límites, autenticación, alias/ID, migración y reembolsos después de
regalar. Las suites de Club, compras y comando de desarrollo conservan sus contratos.
La cobertura nativa requiere 100% de sentencias y ramas. El frontend exige 100% de
líneas, ramas y funciones, además de sus pruebas completas de idiomas.

El arnés opt-in `npm run test:shared-visits -- <repositorio-bot>` usa navegador real,
gateway, API firmada y SQLite temporal. Comprueba regalo por alias, retorno por ID,
errores junto a su botón, viewport reducido, colecciones compartidas y la compra
para regalo con un pago ficticio cancelado. No usa cuentas ni pagos productivos y
no acredita teclado físico o una sesión real de Telegram.

Un candidato fallido usa el snapshot consistente previo al deploy, tras detener el
candidato, mediante [DEPLOY_VPS.md](DEPLOY_VPS.md). Un downgrade manual a un bot sin
soporte de procedencia **no es compatible para seguir operando y luego reutilizar
los lotes**: esas versiones no mantienen el nuevo libro de inventario al comprar,
regalar internamente o reembolsar. Con datos posteriores al lanzamiento, preferir
una corrección compatible; una restauración que pierda cambios requiere evaluación
y autorización específicas. No borrar lotes ni reconstruirlos a ciegas.
