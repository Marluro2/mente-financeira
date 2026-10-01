@echo off
setlocal
title Mente Financeira - Instalacao
cd /d "%~dp0"

rem Cria o ambiente .venv (Python 3.14), instala o Flet e cria os atalhos.
rem Basta executar uma vez. O JOGAR.bat chama este arquivo sozinho, se precisar.

echo ============================================
echo   MENTE FINANCEIRA - instalacao
echo ============================================
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo O Python nao foi encontrado neste computador.
    echo Instale o Python 3.14 em https://www.python.org/downloads/
    echo marcando a opcao "Add python.exe to PATH" e execute este arquivo de novo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando o ambiente do jogo...
    py -3.14 -m venv .venv
    if errorlevel 1 (
        echo Nao foi possivel criar o ambiente. Verifique se o Python 3.14 esta instalado.
        pause
        exit /b 1
    )
)

echo Instalando o Flet ^(pode levar alguns minutos na primeira vez^)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo A instalacao falhou. Verifique a conexao com a internet e tente de novo.
    pause
    exit /b 1
)

call "%~dp0CRIAR_ATALHOS.bat" auto

echo.
echo Instalacao concluida! Para jogar, clique duas vezes em JOGAR.bat
echo ou no atalho "Mente Financeira" desta pasta.
if /i not "%~1"=="auto" pause
exit /b 0
