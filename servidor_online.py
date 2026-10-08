"""Servidor do modo online do Mente Financeira (sala de espera e duelo).

O site do GitHub Pages continua igual. Este servidor é à parte: roda o mesmo
jogo em modo servidor do Flet, para duas pessoas jogarem de computadores
diferentes, e responde em ``/api/online`` quantas pessoas estão no modo online
em cada trilha (o site mostra esse número na página das trilhas).

Tudo fica só na memória: ao sair, o apelido e a partida somem.

Rodar no computador:  python servidor_online.py   (abre em http://localhost:8000)
Hospedagem: veja render.yaml e a seção "Modo online" do README.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import flet_web.fastapi as flet_fastapi

from mente_financeira.online.app import make_main, new_lobby

ASSETS_DIR = str(Path(__file__).resolve().parent / "assets")
SESSION_TIMEOUT_SECONDS = 30  # quem fecha a página sai da sala depois disso

# Qualquer site pode ler a contagem (é só um número por trilha).
OPEN_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Cross-Origin-Resource-Policy": "cross-origin",
    "Cache-Control": "no-store",
}


def create_app() -> FastAPI:
    lobby = new_lobby()
    server = FastAPI(title="Mente Financeira online", docs_url=None, redoc_url=None, openapi_url=None)

    @server.get("/api/online")
    def online() -> JSONResponse:
        return JSONResponse(lobby.counts(), headers=OPEN_HEADERS)

    # Por último: o jogo ocupa todos os outros endereços.
    server.mount(
        "/",
        flet_fastapi.app(
            make_main(lobby),
            assets_dir=ASSETS_DIR,
            app_name="Mente Financeira",
            session_timeout_seconds=SESSION_TIMEOUT_SECONDS,
            no_cdn=os.getenv("MENTE_FINANCEIRA_NO_CDN") == "1",
        ),
    )
    return server


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), proxy_headers=True, forwarded_allow_ips="*")
