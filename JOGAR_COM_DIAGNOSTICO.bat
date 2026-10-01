@echo off
setlocal
title Mente Financeira - Diagnostico
cd /d "%~dp0"

rem Igual ao JOGAR.bat, mas mostra os registros nesta janela.
rem Use quando o jogo nao abrir. Acrescente --admin para o modo administrador.

if not exist ".venv\Scripts\python.exe" (
    echo O jogo ainda nao foi instalado. Execute INSTALAR.bat primeiro.
    pause
    exit /b 1
)

echo Iniciando o jogo com registros visiveis...
echo Feche a janela do jogo para encerrar o diagnostico.
echo.
".venv\Scripts\python.exe" "%~dp0iniciar_janela_app.py" --diagnostico %*
set "CODIGO=%errorlevel%"
if not "%CODIGO%"=="0" (
    echo.
    echo O jogo terminou com o codigo %CODIGO%.
    echo Consulte o arquivo registros\iniciador.log
    pause
)
exit /b %CODIGO%
