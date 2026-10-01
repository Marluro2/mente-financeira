"""Ponto de entrada do Mente Financeira (Python 3.14 + Flet 0.86).

A lógica do jogo fica no pacote ``mente_financeira``. Este arquivo apenas
escolhe como abrir a interface e inicia o aplicativo; ``flet build`` também
procura por ``main.py`` como ponto de entrada.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

import flet as ft

from mente_financeira.storage import SettingsStore, connect_browser_storage
from mente_financeira.ui.shell import GameShell

# Ilustrações das cartas (assets/cartas). Caminho absoluto: funciona mesmo
# quando o jogo é iniciado a partir de outra pasta.
ASSETS_DIR = str(Path(__file__).resolve().parent / "assets")


def running_in_browser() -> bool:
    """True no jogo publicado como site (o Python roda dentro da página)."""

    return sys.platform == "emscripten"


async def main(page: ft.Page) -> None:
    store = SettingsStore()
    if running_in_browser():
        # No site, as preferências (som, paleta) ficam no navegador do jogador.
        await connect_browser_storage(store, ft.SharedPreferences(), page.run_task)
    GameShell(page, store=store)


def select_app_view(
    platform: str | None = None,
    configured_view: str | None = None,
) -> ft.AppView:
    """Seleciona uma inicialização compatível com políticas do Windows.

    Alguns ambientes institucionais bloqueiam o executável auxiliar do cliente
    desktop do Flet (WinError 4551). O modo web usa o navegador já autorizado e
    não tenta executar esse arquivo. A variável ``MENTE_FINANCEIRA_VIEW`` pode
    ser definida como ``web`` ou ``desktop`` para substituir a escolha automática.
    """

    current_platform = platform or sys.platform
    requested = (
        configured_view if configured_view is not None else os.getenv("MENTE_FINANCEIRA_VIEW", "")
    ).strip().lower()

    if requested == "web":
        return ft.AppView.WEB_BROWSER
    if requested == "desktop":
        return ft.AppView.FLET_APP
    return ft.AppView.WEB_BROWSER if current_platform == "win32" else ft.AppView.FLET_APP


def run_app() -> None:
    view = select_app_view()
    # Restringe o servidor web ao computador local; nenhuma porta fica exposta
    # para outros dispositivos da rede.
    host = "127.0.0.1" if view == ft.AppView.WEB_BROWSER else None
    ft.run(main, view=view, host=host, assets_dir=ASSETS_DIR)


# No site (flet build web) este arquivo pode ser carregado como módulo, e não
# como programa principal; por isso o jogo também inicia quando está no navegador.
if __name__ == "__main__" or running_in_browser():
    run_app()
