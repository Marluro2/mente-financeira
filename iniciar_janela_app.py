"""Iniciador do Mente Financeira em janela própria no Windows.

Adaptado do iniciador do "Responda ou Estuda". O jogo continua usando o
servidor local do Flet, mas a interface abre em MODO APLICATIVO do Microsoft
Edge (ou do Google Chrome): janela própria, maximizada, sem abas, barra de
endereço ou menus. Assim não é preciso executar o ``flet.exe``, que o Controle
Inteligente de Aplicativos do Windows costuma bloquear (WinError 4551).

Uso (normalmente pelos arquivos .bat ou pelos atalhos da pasta):
    pythonw iniciar_janela_app.py              -> jogo
    pythonw iniciar_janela_app.py --admin      -> modo administrador
    python  iniciar_janela_app.py --diagnostico -> mostra os registros

Este arquivo usa apenas a biblioteca padrão do Python.
"""

from __future__ import annotations

import argparse
import ctypes
import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

PASTA_APP = Path(__file__).resolve().parent
ARQUIVO_PRINCIPAL = PASTA_APP / "main.py"
PASTA_REGISTROS = PASTA_APP / "registros"
ARQUIVO_LOG = PASTA_REGISTROS / "iniciador.log"
NOME_MUTEX = "Local\\MenteFinanceira_JanelaApp_2026"
TEMPO_LIMITE_SERVIDOR = 90.0
TITULO = "Mente Financeira"

_HANDLE_MUTEX: int | None = None


def _configurar_log(diagnostico: bool) -> None:
    PASTA_REGISTROS.mkdir(parents=True, exist_ok=True)
    manipuladores: list[logging.Handler] = [logging.FileHandler(ARQUIVO_LOG, encoding="utf-8")]
    if diagnostico:
        manipuladores.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=manipuladores,
        force=True,
    )


def _mostrar_mensagem(texto: str, erro: bool = False) -> None:
    """Mostra um aviso mesmo quando o iniciador roda por pythonw (sem console)."""

    if os.name == "nt":
        icone = 0x10 if erro else 0x40  # MB_ICONERROR ou MB_ICONINFORMATION
        ctypes.windll.user32.MessageBoxW(0, texto, TITULO, icone)
    else:
        print(f"{TITULO}: {texto}", file=sys.stderr if erro else sys.stdout)


def _obter_execucao_exclusiva(admin: bool) -> bool:
    """Impede que o mesmo modo seja aberto duas vezes ao mesmo tempo."""

    global _HANDLE_MUTEX
    if os.name != "nt":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    criar_mutex = kernel32.CreateMutexW
    criar_mutex.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    criar_mutex.restype = ctypes.c_void_p
    ctypes.set_last_error(0)
    handle = criar_mutex(None, False, NOME_MUTEX + ("_Admin" if admin else ""))
    if not handle:
        raise OSError(ctypes.get_last_error(), "Não foi possível criar o mutex")
    _HANDLE_MUTEX = int(handle)
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        _mostrar_mensagem("O jogo já está aberto. Verifique a barra de tarefas.")
        return False
    return True


def _porta_local_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind(("127.0.0.1", 0))
        return int(servidor.getsockname()[1])


def _python_do_servidor() -> Path:
    """Python com console do ambiente do projeto (.venv); senão, o atual."""

    venv = PASTA_APP / ".venv" / "Scripts" / "python.exe"
    if venv.is_file():
        return venv
    executavel = Path(sys.executable)
    if executavel.name.lower() == "pythonw.exe":
        candidato = executavel.with_name("python.exe")
        if candidato.exists():
            return candidato
    return executavel


def _iniciar_servidor(porta: int, admin: bool, log_servidor) -> subprocess.Popen:
    ambiente = os.environ.copy()
    ambiente.update(
        {
            # O Flet inicia só o servidor local: nenhuma aba comum é aberta.
            "FLET_FORCE_WEB_SERVER": "true",
            "FLET_SERVER_IP": "127.0.0.1",
            "FLET_SERVER_PORT": str(porta),
            "FLET_DISPLAY_URL_PREFIX": "APP_LOCAL",
            "PYTHONUTF8": "1",
        }
    )
    if admin:
        ambiente["MENTE_ADMIN"] = "1"
    else:
        ambiente.pop("MENTE_ADMIN", None)
    return subprocess.Popen(
        [str(_python_do_servidor()), str(ARQUIVO_PRINCIPAL)],
        cwd=str(PASTA_APP),
        env=ambiente,
        stdin=subprocess.DEVNULL,
        stdout=log_servidor,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _aguardar_servidor(processo: subprocess.Popen, url: str, limite: float = TEMPO_LIMITE_SERVIDOR) -> None:
    inicio = time.monotonic()
    ultimo_erro = ""
    while time.monotonic() - inicio < limite:
        codigo = processo.poll()
        if codigo is not None:
            raise RuntimeError(f"O servidor local foi encerrado antes da abertura (código {codigo}).")
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resposta:
                if 200 <= resposta.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError) as erro:
            ultimo_erro = str(erro)
        time.sleep(0.25)
    detalhe = f" Último retorno: {ultimo_erro}" if ultimo_erro else ""
    raise TimeoutError("O jogo demorou mais que o esperado para iniciar." + detalhe)


def _localizar_navegador() -> Path:
    """Localiza o Edge e usa o Chrome como alternativa."""

    configurado = os.getenv("MENTE_NAVEGADOR_APP", "").strip().strip('"')
    if configurado and Path(configurado).is_file():
        return Path(configurado)

    candidatos: list[Path] = []
    raizes = [os.getenv("PROGRAMFILES(X86)"), os.getenv("PROGRAMFILES"), os.getenv("PROGRAMW6432"), os.getenv("LOCALAPPDATA")]
    relativos = [Path("Microsoft/Edge/Application/msedge.exe"), Path("Google/Chrome/Application/chrome.exe")]
    for raiz in raizes:
        if raiz:
            candidatos.extend(Path(raiz) / relativo for relativo in relativos)
    for nome in ("msedge.exe", "chrome.exe"):
        encontrado = shutil.which(nome)
        if encontrado:
            candidatos.append(Path(encontrado))
    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    raise FileNotFoundError("Microsoft Edge ou Google Chrome não foi encontrado neste computador.")


def _abrir_janela_aplicativo(navegador: Path, url: str) -> tuple[subprocess.Popen, Path]:
    """Abre a URL numa instância isolada do navegador, em modo aplicativo."""

    perfil_temporario = Path(tempfile.mkdtemp(prefix="mente_financeira_app_"))
    argumentos = [
        str(navegador),
        f"--app={url}",
        f"--user-data-dir={perfil_temporario}",
        "--start-maximized",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-mode",
        "--disable-session-crashed-bubble",
        # Evita o aviso de sincronização da conta Microsoft no Edge.
        "--disable-sync",
        "--disable-features=msImplicitSignin,msEdgeFirstSyncOnFirstRun,msEdgeSyncConsent,msEdgeFrePrelaunchSyncData",
    ]
    processo = subprocess.Popen(
        argumentos,
        cwd=str(PASTA_APP),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    return processo, perfil_temporario


def _encerrar_processo(processo: subprocess.Popen | None) -> None:
    if processo is None or processo.poll() is not None:
        return
    processo.terminate()
    try:
        processo.wait(timeout=6)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait(timeout=3)


def _ultimas_linhas_log(maximo: int = 12) -> str:
    try:
        return "\n".join(ARQUIVO_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-maximo:])
    except OSError:
        return ""


def executar(diagnostico: bool = False, admin: bool = False) -> int:
    _configurar_log(diagnostico)
    logging.info("Iniciando o Mente Financeira em janela própria (admin=%s).", admin)

    if os.name != "nt":
        _mostrar_mensagem("Este iniciador foi preparado para Windows 10 ou 11. Use: python main.py", erro=True)
        return 1
    if not _obter_execucao_exclusiva(admin):
        return 0
    if not ARQUIVO_PRINCIPAL.is_file():
        _mostrar_mensagem("O arquivo main.py não foi encontrado. Copie a pasta do jogo completa.", erro=True)
        return 1

    servidor: subprocess.Popen | None = None
    perfil_temporario: Path | None = None
    log_servidor = None
    try:
        navegador = _localizar_navegador()
        porta = _porta_local_livre()
        url = f"http://127.0.0.1:{porta}/"
        logging.info("Navegador: %s | Endereço local: %s", navegador, url)

        log_servidor = ARQUIVO_LOG.open("a", encoding="utf-8")
        servidor = _iniciar_servidor(porta, admin, log_servidor)
        _aguardar_servidor(servidor, url)
        logging.info("Servidor pronto. Abrindo a janela do jogo.")

        janela, perfil_temporario = _abrir_janela_aplicativo(navegador, url)
        janela.wait()
        logging.info("A janela foi fechada.")
        return 0
    except Exception as erro:
        logging.exception("Falha ao iniciar o jogo")
        texto = f"Não foi possível abrir o jogo.\n\n{erro}\n\nConsulte o arquivo:\n{ARQUIVO_LOG}"
        detalhes = _ultimas_linhas_log()
        if diagnostico and detalhes:
            texto += f"\n\nÚltimos registros:\n{detalhes}"
        _mostrar_mensagem(texto, erro=True)
        return 1
    finally:
        _encerrar_processo(servidor)
        if log_servidor is not None:
            log_servidor.close()
        if perfil_temporario is not None:
            shutil.rmtree(perfil_temporario, ignore_errors=True)
        logging.info("Iniciador encerrado.")


def main() -> int:
    analisador = argparse.ArgumentParser(description="Abre o Mente Financeira em janela própria.")
    analisador.add_argument("--diagnostico", action="store_true", help="Também mostra os registros no console.")
    analisador.add_argument("--admin", action="store_true", help="Abre no modo administrador.")
    argumentos = analisador.parse_args()
    return executar(diagnostico=argumentos.diagnostico, admin=argumentos.admin)


if __name__ == "__main__":
    raise SystemExit(main())
