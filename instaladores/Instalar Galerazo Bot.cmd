@echo off
chcp 65001 >nul
setlocal

set "RAIZ_DEL_PROYECTO=%~dp0.."
set "SCRIPT_DE_PREPARACION=%RAIZ_DEL_PROYECTO%\scripts\setup.ps1"

if not exist "%SCRIPT_DE_PREPARACION%" (
    echo No se encontro el script de preparacion en "%SCRIPT_DE_PREPARACION%".
    set "CODIGO_DE_SALIDA=1"
    goto finalizar
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DE_PREPARACION%" %*
set "CODIGO_DE_SALIDA=%ERRORLEVEL%"

:finalizar
echo.
if "%CODIGO_DE_SALIDA%"=="0" (
    echo Instalacion terminada. El panel de Galerazo Bot ya esta listo.
) else (
    echo La instalacion termino con codigo %CODIGO_DE_SALIDA%. Revisa los mensajes anteriores.
)

pause
exit /b %CODIGO_DE_SALIDA%
