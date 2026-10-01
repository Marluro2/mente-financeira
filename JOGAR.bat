@echo off
setlocal
title Mente Financeira
cd /d "%~dp0"

rem Abre o jogo em janela propria (sem terminal e sem abas do navegador).
rem Na primeira vez, instala tudo automaticamente.

if not exist ".venv\Scripts\pythonw.exe" (
    echo Primeira execucao: preparando o jogo...
    call "%~dp0INSTALAR.bat" auto
    if errorlevel 1 exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "%~dp0iniciar_janela_app.py"
exit /b 0
