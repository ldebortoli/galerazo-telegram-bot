# Instalador local de Galerazo Bot

En Windows, hace doble clic en `Instalar Galerazo Bot.cmd`. El instalador llama al setup versionado del proyecto y:

- instala la version exacta de Python indicada en `.python-version` mediante `winget` cuando hace falta;
- crea o reutiliza `.venv` e instala el lock completo de dependencias;
- ejecuta la suite y valida el runtime;
- crea `.env` desde `.env.example` solamente si todavia no existe;
- compila `GalerazoBotControl.exe` con el icono del proyecto;
- crea accesos directos en `CODEX APPS` y en el Escritorio;
- abre el panel para configurarlo y probarlo localmente.

El instalador no copia el bot a otra ubicacion ni incluye secretos. Todo continua ejecutandose desde este repositorio. Volver a abrirlo actualiza dependencias y reconstruye la UI sin reemplazar `.env`.

Tambien se puede ejecutar desde PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Opciones disponibles:

- `-SkipTests`: omite la suite durante esa instalacion.
- `-NoLaunch`: prepara todo sin abrir el panel al finalizar.
- `-ForceRecreate`: recrea `.venv` aunque ya use el Python correcto.
