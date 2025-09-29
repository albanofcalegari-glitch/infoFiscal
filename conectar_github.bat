@echo off
title Conectar con GitHub
color 0E

echo.
echo ========================================================
echo 🚀 CONECTAR PROYECTO CON GITHUB
echo ========================================================
echo.

echo 📋 ANTES DE EJECUTAR ESTE SCRIPT:
echo 1. Crear repositorio "infofiscal" en GitHub
echo 2. Tener tu usuario de GitHub listo
echo.

set /p usuario="Ingresa tu USUARIO de GitHub: "
if "%usuario%"=="" (
    echo ❌ Usuario requerido
    pause
    exit
)

echo.
echo 🔗 Conectando con: https://github.com/%usuario%/infofiscal.git
echo.

REM Conectar repositorio remoto
git remote add origin https://github.com/%usuario%/infofiscal.git
if %errorlevel% neq 0 (
    echo ⚠️ El repositorio remoto ya existe o hay un error
    echo Ejecutando: git remote set-url origin https://github.com/%usuario%/infofiscal.git
    git remote set-url origin https://github.com/%usuario%/infofiscal.git
)

REM Cambiar a rama main
echo 🔄 Cambiando a rama main...
git branch -M main

REM Subir código
echo 📤 Subiendo código a GitHub...
git push -u origin main

if %errorlevel%==0 (
    echo.
    echo ✅ ¡PROYECTO SUBIDO EXITOSAMENTE!
    echo.
    echo 🔗 Tu proyecto está disponible en:
    echo    https://github.com/%usuario%/infofiscal
    echo.
    echo 🎉 ¡Comparte el enlace con quien quieras!
) else (
    echo.
    echo ❌ Error al subir. Posibles causas:
    echo - Repositorio no existe en GitHub
    echo - Problemas de autenticación
    echo - Nombre de usuario incorrecto
    echo.
    echo 💡 Verifica y vuelve a ejecutar el script
)

echo.
pause