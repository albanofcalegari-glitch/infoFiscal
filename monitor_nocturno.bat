@echo off
title Monitor AFIP NOCTURNO - Verificando cada 5 min
color 0A
echo.
echo ============================================================
echo 🌙 MONITOR AFIP NOCTURNO - Verificacion cada 5 minutos
echo ============================================================
echo CUIT: 20-32151804-5
echo Hora inicio: %date% %time%
echo Log guardado en: monitor_log.txt
echo.
echo 💤 Puedes cerrar esta ventana, seguira verificando
echo 🔔 Te avisara con SONIDO cuando este listo
echo.

REM Crear archivo de log
echo [%date% %time%] MONITOR AFIP INICIADO > monitor_log.txt
echo CUIT: 20-32151804-5 >> monitor_log.txt
echo ================================================== >> monitor_log.txt

set contador=1

:loop
echo [%time%] Verificacion #%contador%... >> monitor_log.txt
echo [%time%] Verificacion #%contador%...

REM Ejecutar verificacion
".venv\Scripts\python.exe" verificar_servicios.py > temp_result.txt 2>&1

REM Buscar si los servicios estan activos
findstr /C:"SERVICIOS AFIP FUNCIONANDO" temp_result.txt >nul
if %errorlevel%==0 (
    echo. >> monitor_log.txt
    echo [%date% %time%] 🎉 SERVICIOS ACTIVOS DETECTADOS! >> monitor_log.txt
    echo ============================================== >> monitor_log.txt
    echo PROXIMOS PASOS: >> monitor_log.txt
    echo 1. python cambiar_modo.py produccion >> monitor_log.txt
    echo 2. Reiniciar aplicacion Flask >> monitor_log.txt
    echo 3. Descargar facturas reales >> monitor_log.txt
    echo ============================================== >> monitor_log.txt
    
    cls
    color 0E
    echo.
    echo ============================================================
    echo 🎉 ^!^!^! AFIP ACTIVO ^!^!^!
    echo ============================================================
    echo Hora activacion: %date% %time%
    echo.
    echo 📋 PROXIMOS PASOS:
    echo 1. Ejecutar: python cambiar_modo.py produccion
    echo 2. Reiniciar la aplicacion Flask
    echo 3. ^!Ya puedes descargar facturas REALES^!
    echo.
    echo ✅ Detalles guardados en monitor_log.txt
    echo.
    
    REM SONIDOS DE NOTIFICACION - MULTIPLES BEEPS
    for /l %%i in (1,1,10) do (
        echo 
        timeout /t 1 /nobreak >nul
    )
    
    echo.
    echo 🔔 PRESIONA CUALQUIER TECLA PARA CONTINUAR...
    del temp_result.txt
    pause >nul
    exit
) else (
    echo    ⏳ Servicios pendientes... >> monitor_log.txt
    echo    ⏳ Servicios pendientes... Siguiente: %time%
    
    REM Esperar 5 minutos = 300 segundos
    timeout /t 300 /nobreak >nul
    
    set /a contador+=1
)

del temp_result.txt
goto loop