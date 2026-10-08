"""Duelo em sala: o notebook vira o servidor do jogo, sem precisar de internet.

Feito para a feira: o notebook e os celulares ficam no mesmo Wi-Fi (um
roteador do estande). Os celulares abrem o endereço do notebook no navegador,
uma pessoa cria a sala e a outra entra com o código (ex.: GATO-42) ou pelo QR
code. Tudo vem do notebook, inclusive os emojis. Nada é gravado: apelidos e
partidas ficam só na memória e somem quando a pessoa sai.

Iniciar:  python servidor_sala.py      (no Windows: JOGAR_FEIRA.bat)
Guia da feira: docs/GUIA_FEIRA.md
"""

from __future__ import annotations

import html
import io
import os
from pathlib import Path
import socket
import threading
import webbrowser

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
import flet_web.fastapi as flet_fastapi
import segno

from mente_financeira.sala.app import make_main, new_lobby
from mente_financeira.sala.salas import RoomError, normalize_code

ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
EMOJI_FONT = ASSETS_DIR / "fontes" / "emoji.woff2"
PORT = int(os.getenv("PORT", "8000"))
SESSION_TIMEOUT_SECONDS = 30  # quem fecha a página sai da sala depois disso
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def lan_address() -> str:
    """IP do notebook na rede do roteador (o que os celulares usam)."""

    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))  # não envia nada; só escolhe a placa de rede
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def qr_png(text: str) -> Response:
    buffer = io.BytesIO()
    segno.make(text, error="m").save(buffer, kind="png", scale=10, border=2, dark="#12082E")
    return Response(buffer.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


def create_app(lan_url: str | None = None) -> FastAPI:
    lobby = new_lobby()
    lan_url = lan_url or f"http://{lan_address()}:{PORT}"
    server = FastAPI(title="Mente Financeira em sala", docs_url=None, redoc_url=None, openapi_url=None)

    def public_url(request: Request) -> str:
        # No próprio notebook (localhost), o QR precisa do IP da rede, não de "localhost".
        if request.url.hostname in LOCAL_HOSTS:
            return lan_url
        return str(request.base_url).rstrip("/")

    @server.get("/qr/sala/{code}.png")
    def room_qr(code: str, request: Request) -> Response:
        try:
            code = normalize_code(code)
        except RoomError:
            return Response(status_code=404)
        return qr_png(f"{public_url(request)}/?sala={code}")

    @server.get("/qr/mesa.png")
    def table_qr(request: Request) -> Response:
        return qr_png(public_url(request) + "/")

    @server.get("/mesa", response_class=HTMLResponse)
    def table_page(request: Request) -> str:
        """Cartaz para a mesa do estande: QR code e endereço do jogo."""

        address = html.escape(public_url(request))
        return TABLE_PAGE.replace("{address}", address)

    @server.get("/assets/fonts/notocoloremoji/{rest:path}")
    def emoji_font(rest: str) -> FileResponse:
        # O Flet pediria os emojis à internet; aqui eles vêm do notebook.
        return FileResponse(EMOJI_FONT, media_type="font/woff2")

    # Por último: o jogo ocupa todos os outros endereços.
    server.mount(
        "/",
        flet_fastapi.app(
            make_main(lobby),
            assets_dir=str(ASSETS_DIR),
            app_name="Mente Financeira",
            no_cdn=True,  # sem internet: o Flet usa só os arquivos instalados
            session_timeout_seconds=SESSION_TIMEOUT_SECONDS,
        ),
    )
    return server


TABLE_PAGE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mente Financeira • Duelo em sala</title>
<style>
  body { margin: 0; font-family: system-ui, sans-serif; background: #1B0B3B; color: #fff;
         display: flex; min-height: 100vh; align-items: center; justify-content: center; text-align: center; }
  main { padding: 32px; }
  h1 { font-size: 56px; margin: 0; color: #FFD23F; }
  h2 { font-size: 28px; margin: 4px 0 24px; color: #3DD9FF; }
  img { display: block; margin: 0 auto; width: min(70vw, 420px); background: #fff; border-radius: 24px; padding: 16px; }
  ol { font-size: 22px; line-height: 1.6; text-align: left; display: inline-block; margin: 24px 0 8px; }
  code { font-size: 26px; color: #FFD23F; }
  p { color: #CFC7F2; }
  @media print { body { background: #fff; color: #000; } h1, h2, code { color: #000; } p { color: #333; } }
</style></head>
<body><main>
  <h1>MENTE FINANCEIRA</h1>
  <h2>Duelo em sala: jogue contra um amigo!</h2>
  <img src="/qr/mesa.png" alt="QR code do jogo">
  <ol>
    <li>Conecte o celular no <b>Wi-Fi do estande</b>.</li>
    <li>Escaneie o QR code ou abra <code>{address}</code></li>
    <li>Uma pessoa cria a sala; a outra entra com o código.</li>
  </ol>
  <p>Se o celular avisar "sem internet", escolha continuar conectado neste Wi-Fi.</p>
</main></body></html>
"""


def main() -> None:
    import uvicorn

    lan_url = f"http://{lan_address()}:{PORT}"
    print("=" * 60)
    print(" Mente Financeira • Duelo em sala")
    print(f" Celulares (mesmo Wi-Fi): {lan_url}")
    print(f" Cartaz com QR code:      http://localhost:{PORT}/mesa")
    print(" Para encerrar, feche esta janela.")
    print("=" * 60)
    if os.getenv("MENTE_FINANCEIRA_SEM_NAVEGADOR") != "1":
        threading.Timer(2.0, webbrowser.open, (f"http://localhost:{PORT}/mesa",)).start()
    uvicorn.run(create_app(lan_url), host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
