@echo off
title Monitor AFIP - Verificacion automatica
color 0E
echo.
echo ============================================================
echo 🔍 MONITOR AFIP - Verificacion automatica cada 5 minutos
echo ============================================================
echo CUIT: 20-32151804-5
echo Presiona Ctrl+C para detener
echo.

set contador=1

:loop
echo [%time%] Verificacion #%contador%...

REM Ejecutar verificacion
".venv\Scripts\python.exe" verificar_servicios.py > temp_result.txt 2>&1

REM Buscar si los servicios estan activos
findstr /C:"SERVICIOS AFIP FUNCIONANDO" temp_result.txt >nul
if %errorlevel%==0 (
    echo.
    echo 🎉 ^!EXCELENTE^! ^!SERVICIOS ACTIVOS^!
    echo.
    echo 📋 PROXIMOS PASOS:
    echo 1. Ejecutar: python cambiar_modo.py produccion
    echo 2. Reiniciar la aplicacion Flask
    echo 3. ^!Ya puedes descargar facturas reales^!
    echo.
    
    REM Sonido de notificacion
    echo 
    
    del temp_result.txt
    pause
    exit
) else (
    echo    ⏳ Servicios pendientes de activacion
    echo    Proxima verificacion en 5 minutos...
    echo.
    
    REM Esperar 5 minutos = 300 segundos
    timeout /t 300 /nobreak >nul
    
    set /a contador+=1
)

del temp_result.txt
goto loop