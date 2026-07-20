# Session handoff

## Objetivo general

Mantener y ampliar Galerazo Bot como bot de Telegram modular y reanudable, con SQLite como fuente de verdad y el mismo runtime reproducible en Windows, CI y Docker.

## Tarea actual

El setup integral y el instalador local de Windows estan implementados, ejecutados y publicados.

## Estado actual

- Rama `main`, tracking `origin/main`.
- Python 3.14.6 exacto en `.venv`, Docker y CI; lock sin paquetes desactualizados.
- `scripts/setup.ps1` compone sincronizacion de runtime, configuracion inicial, directorios locales, build, accesos directos y apertura del panel.
- `scripts/sync_windows_runtime.ps1` conserva una `.venv` con la version exacta, instala el lock y solo recrea ante ausencia, version incorrecta o `-ForceRecreate`. Rechaza borrar enlaces/junctions.
- `build_control_panel.ps1` valida icono/compilador/resultado y crea `Galerazo Bot.lnk` en `CODEX APPS` y Escritorio.
- `instaladores/Instalar Galerazo Bot.cmd` es el instalador de doble clic y delega al setup versionado.
- El setup crea `.env` desde `.env.example` solo cuando falta. La ejecucion real conservo el `.env` existente y no expuso secretos.
- El setup real conservo `.venv`, verifico dependencias, paso 82 pruebas, recompilo `bin/GalerazoBotControl.exe`, creo ambos accesos y abrio la UI.
- La ventana `Galerazo Bot - Control` esta abierta bajo `pythonw` PID 10416. No se inicio el bot automaticamente.
- `USER_QUEUE.md` no tiene pedidos sin procesar.

## Validacion reciente

- Parser PowerShell: sintaxis OK para `scripts/setup.ps1`, `scripts/sync_windows_runtime.ps1` y `build_control_panel.ps1`.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1`: OK de punta a punta.
- Suite ejecutada por el setup: 82 pruebas OK.
- `scripts/runtime_versions.py`: Python 3.14.6 y lock alineados.
- `pip check`: sin dependencias rotas.
- El setup tambien ejecuta `compileall` sobre entrypoints, paquete y scripts.
- Accesos verificados: ambos apuntan a `bin/GalerazoBotControl.exe`, usan el root como working directory y el ICO correcto.
- `git diff --check`: limpio antes del cierre final.
- Commit `6ab45b4` publicado en `main`; Quality `29760863385` paso completo. Docker Quality no se disparo porque no cambiaron el runtime ni el lock.

## Proximos pasos

1. Para una nueva instalacion, abrir `instaladores\Instalar Galerazo Bot.cmd`; para actualizar esta PC, se puede volver a ejecutar el mismo archivo.
2. Cargar una API key restringida a `/v1/moderations` desde el panel cuando se quiera activar moderacion real.
3. Mantener bloqueados Google Sheets real y Railway hasta recibir los inputs/autorizacion correspondientes.

## Riesgos y bloqueos

- El instalador es nativo de Windows y depende de `winget` solo si falta el Python exacto. No instala Docker ni produce un paquete autonomo.
- Google Sheets real esta bloqueado hasta que el usuario confirme spreadsheet ID, worksheet y credenciales de service account.
- Railway requiere pedido explicito y los secrets correspondientes.
- La consulta del medio de pago de GitHub requiere iniciar sesion o autorizar ampliar el scope de `gh`; no se ampliaron permisos.

## Archivos modificados

- `scripts/setup.ps1`, `scripts/sync_windows_runtime.ps1`
- `build_control_panel.ps1`
- `instaladores/Instalar Galerazo Bot.cmd`, `instaladores/README.md`
- `tests/test_setup.py`
- `README.md`
- `.codex/CONTEXT.md`, `.codex/DECISIONS.md`, `.codex/BACKLOG.md`, `.codex/SESSION_HANDOFF.md`
