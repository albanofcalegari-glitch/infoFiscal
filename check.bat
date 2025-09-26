@echo off
echo 🔍 Verificacion rapida AFIP...
".venv\Scripts\python.exe" verificar_servicios.py
echo.
echo 💡 Para monitoreo automatico: .\monitor_afip.bat