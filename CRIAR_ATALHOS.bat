@echo off
setlocal
cd /d "%~dp0"

rem Cria nesta pasta os atalhos "Mente Financeira" e
rem "Mente Financeira (Administrador)", com o icone do jogo.
rem Execute de novo se a pasta do jogo mudar de lugar.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0criar_atalhos.ps1"
if /i not "%~1"=="auto" pause
