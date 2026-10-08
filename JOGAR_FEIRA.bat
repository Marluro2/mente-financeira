@echo off
setlocal
title Mente Financeira - Duelo em sala (feira)
cd /d "%~dp0"

rem Transforma este notebook no servidor do jogo para a feira.
rem Os celulares no mesmo Wi-Fi abrem o endereco mostrado abaixo.
rem Nao precisa de internet durante a feira (so na instalacao).
rem Guia completo: docs\GUIA_FEIRA.md

if not exist ".venv\Scripts\python.exe" (
    call "%~dp0INSTALAR.bat" auto
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -c "import segno" >nul 2>&1
if errorlevel 1 (
    echo Instalando o que falta para o Duelo em sala ^(precisa de internet^)...
    call "%~dp0INSTALAR.bat" auto
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" "%~dp0servidor_sala.py"
pause
