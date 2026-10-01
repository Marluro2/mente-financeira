@echo off
setlocal
title Mente Financeira - Modo Administrador
cd /d "%~dp0"

rem MODO ADMINISTRADOR (para o professor): Painel do professor com todos os
rem conceitos, desafios e questoes com gabarito; cronometro desligado;
rem "Mostrar gabarito" no jogo da memoria; preferencias separadas.
rem Pode ficar aberto ao mesmo tempo que o jogo normal.

if not exist ".venv\Scripts\pythonw.exe" (
    echo Primeira execucao: preparando o jogo...
    call "%~dp0INSTALAR.bat" auto
    if errorlevel 1 exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "%~dp0iniciar_janela_app.py" --admin
exit /b 0
