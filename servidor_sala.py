"""Duelo em sala: o notebook vira o servidor do jogo, sem precisar de internet.

Feito para a feira: o notebook e os celulares ficam no mesmo Wi-Fi (um
roteador do estande). Os celulares abrem o endereço do notebook no navegador,
uma pessoa cria a sala e a outra entra com o código (ex.: GATO-42) ou pelo QR
code. Tudo vem do notebook, inclusive os emojis. Nada é gravado: apelidos e
partidas ficam só na memória e somem quando a pessoa sai; o ranking do dia
(melhores apelidos do Duelo e do Quiz) aparece no cartaz e some ao fechar.

Quiz ao vivo: o notebook abre http://localhost:8000/?quiz=apresentar (vira o
telão) e o público responde pelo celular, entrando pelo QR code da tela.

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
from urllib.parse import urlparse
import webbrowser

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
import flet_web.fastapi as flet_fastapi
import segno

from mente_financeira.sala.app import new_lobby
from mente_financeira.sala.entrada import make_main
from mente_financeira.sala.quiz_app import PLAY, PRESENT, is_local, new_quiz
from mente_financeira.sala.ranking import BOARDS, FairRanking
from mente_financeira.sala.salas import RoomError, normalize_code
from mente_financeira.sugestoes import SuggestionBox

ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
EMOJI_FONT = ASSETS_DIR / "fontes" / "emoji.woff2"
# Sugestões deixadas na feira (anônimas). Abre no Excel.
SUGGESTIONS_FILE = ROOT / "sugestoes" / "sugestoes.csv"
PORT = int(os.getenv("PORT", "8000"))
SESSION_TIMEOUT_SECONDS = 30  # quem fecha a página sai da sala depois disso
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
QUIZ_PLAY_PATH = f"/?quiz={PLAY}"
QUIZ_HOST_PATH = f"/?quiz={PRESENT}"


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


def create_app(lan_url: str | None = None, suggestions: SuggestionBox | None = None) -> FastAPI:
    lobby = new_lobby()
    quiz = new_quiz()
    ranking = FairRanking()
    suggestions = suggestions or SuggestionBox(SUGGESTIONS_FILE)
    lan_url = lan_url or f"http://{lan_address()}:{PORT}"
    own_ips = [urlparse(lan_url).hostname or ""]
    server = FastAPI(title="Mente Financeira em sala", docs_url=None, redoc_url=None, openapi_url=None)
    server.state.ranking = ranking

    def from_notebook(request: Request) -> bool:
        """Só o próprio notebook pode tirar apelidos do ranking."""

        return is_local(request.client.host if request.client else None, own_ips)

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

    @server.get("/qr/quiz.png")
    def quiz_qr(request: Request) -> Response:
        return qr_png(public_url(request) + QUIZ_PLAY_PATH)

    @server.get("/qr/mesa.png")
    def table_qr(request: Request) -> Response:
        return qr_png(public_url(request) + "/")

    @server.get("/mesa", response_class=HTMLResponse)
    def table_page(request: Request) -> str:
        """Cartaz para a mesa do estande: QR code e endereço do jogo."""

        address = html.escape(public_url(request))
        return TABLE_PAGE.replace("{address}", address).replace("{quiz_host}", QUIZ_HOST_PATH)

    @server.get("/ranking")
    def ranking_data(request: Request) -> dict[str, object]:
        """Placar do dia para o cartaz (atualizado a cada poucos segundos)."""

        return {**ranking.as_dict(), "admin": from_notebook(request)}

    @server.post("/ranking/remover")
    def ranking_remove(request: Request, board: str, nickname: str) -> Response:
        if not from_notebook(request) or board not in BOARDS:
            return Response(status_code=403)
        ranking.remove(board, nickname)
        return Response(status_code=204)

    @server.post("/ranking/limpar")
    def ranking_clear(request: Request) -> Response:
        if not from_notebook(request):
            return Response(status_code=403)
        ranking.clear()
        return Response(status_code=204)

    @server.get("/assets/fonts/notocoloremoji/{rest:path}")
    def emoji_font(rest: str) -> FileResponse:
        # O Flet pediria os emojis à internet; aqui eles vêm do notebook.
        return FileResponse(EMOJI_FONT, media_type="font/woff2")

    # Por último: o jogo ocupa todos os outros endereços.
    server.mount(
        "/",
        flet_fastapi.app(
            make_main(
                lobby,
                quiz,
                suggestions.save,
                join_url=lan_url + QUIZ_PLAY_PATH,
                own_ips=own_ips,
                ranking=ranking,
            ),
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
  main { padding: 32px; display: flex; flex-wrap: wrap; gap: 48px; align-items: center; justify-content: center; }
  h1 { font-size: 56px; margin: 0; color: #FFD23F; }
  h2 { font-size: 28px; margin: 4px 0 24px; color: #3DD9FF; }
  img { display: block; margin: 0 auto; width: min(70vw, 420px); background: #fff; border-radius: 24px; padding: 16px; }
  ol { font-size: 22px; line-height: 1.6; text-align: left; display: inline-block; margin: 24px 0 8px; }
  code { font-size: 26px; color: #FFD23F; }
  p { color: #CFC7F2; }
  .quiz a { display: inline-block; margin-top: 12px; padding: 12px 22px; border-radius: 999px;
            background: #FF3D8B; color: #fff; font-weight: 800; text-decoration: none; }
  aside { box-sizing: border-box; width: min(100%, 440px); text-align: left; background: rgba(255,255,255,.08);
          border: 1px solid rgba(255,255,255,.2); border-radius: 28px; padding: 24px 28px; }
  aside h3 { margin: 0 0 4px; font-size: 30px; color: #FFD23F; text-align: center; }
  aside .sub { margin: 0 0 12px; text-align: center; font-size: 14px; }
  aside h4 { margin: 18px 0 6px; font-size: 20px; color: #3DD9FF; }
  aside ol { display: block; margin: 0; padding: 0; list-style: none; font-size: 19px; line-height: 1.4; }
  aside li { display: flex; gap: 10px; align-items: baseline; padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,.08); }
  aside .pos { width: 34px; color: #FFD23F; font-weight: 800; }
  aside .nick { flex: 1; font-weight: 700; }
  aside .det { margin-left: 8px; font-size: 12px; color: #CFC7F2; font-weight: 400; }
  aside .pts { color: #3DD9FF; font-weight: 800; }
  aside .empty { color: #CFC7F2; font-size: 16px; }
  aside button { background: none; border: 0; color: #FF8FB3; font-size: 18px; cursor: pointer; padding: 0 4px; }
  aside .clear { display: block; margin: 16px auto 0; border: 1px solid #FF8FB3; border-radius: 999px; padding: 6px 14px; font-size: 14px; }
  @media (max-width: 600px) { main { padding: 16px; } h1 { font-size: 34px; } ol { font-size: 18px; } code { font-size: 18px; } aside { padding: 18px 16px; } aside .det { display: block; margin-left: 0; } }
  @media print { body { background: #fff; color: #000; } h1, h2, code { color: #000; } p { color: #333; } .quiz, aside { display: none; } }
</style></head>
<body><main>
  <section>
    <h1>MENTE FINANCEIRA</h1>
    <h2>Duelo em sala: jogue contra um amigo!</h2>
    <img src="/qr/mesa.png" alt="QR code do jogo">
    <ol>
      <li>Conecte o celular no <b>Wi-Fi do estande</b>.</li>
      <li>Escaneie o QR code ou abra <code>{address}</code></li>
      <li>Uma pessoa cria a sala; a outra entra com o código.</li>
    </ol>
    <p>Se o celular avisar "sem internet", escolha continuar conectado neste Wi-Fi.</p>
    <p class="quiz"><a href="{quiz_host}">Abrir o Quiz ao vivo (tela do notebook)</a></p>
  </section>
  <aside>
    <h3>🏆 Ranking do dia</h3>
    <p class="sub">Os 5 melhores apelidos do estande. Some quando o jogo fecha.</p>
    <h4>⚔️ Duelo em sala</h4><ol id="duelo"></ol>
    <h4>🎤 Quiz ao vivo</h4><ol id="quiz"></ol>
    <button class="clear" id="limpar" hidden>Limpar ranking</button>
  </aside>
</main>
<script>
// Os apelidos vêm dos celulares: entram sempre como texto (textContent), nunca como HTML.
const MEDALS = ["🥇", "🥈", "🥉"];
const SHOWN = 5;  // cabe na tela do notebook sem rolar
function row(board, entry, index, admin) {
  const li = document.createElement("li");
  const pos = document.createElement("span"); pos.className = "pos"; pos.textContent = MEDALS[index] || (index + 1) + "º";
  const nick = document.createElement("span"); nick.className = "nick"; nick.textContent = entry.nickname;
  const det = document.createElement("span"); det.className = "det"; det.textContent = entry.detail; nick.append(det);
  const pts = document.createElement("span"); pts.className = "pts"; pts.textContent = entry.points.toLocaleString("pt-BR") + " pts";
  li.append(pos, nick, pts);
  if (admin) {
    const out = document.createElement("button"); out.title = "Tirar do ranking"; out.textContent = "✕";
    out.onclick = async () => {
      if (!confirm("Tirar " + entry.nickname + " do ranking?")) return;
      await fetch("/ranking/remover?board=" + board + "&nickname=" + encodeURIComponent(entry.nickname), { method: "POST" });
      load();
    };
    li.append(out);
  }
  return li;
}
async function load() {
  try {
    const data = await (await fetch("/ranking", { cache: "no-store" })).json();
    for (const board of ["duelo", "quiz"]) {
      const list = document.getElementById(board);
      list.replaceChildren(...data[board].slice(0, SHOWN).map((entry, i) => row(board, entry, i, data.admin)));
      if (!data[board].length) {
        const li = document.createElement("li"); li.className = "empty"; li.textContent = "Ninguém ainda: jogue e apareça aqui!";
        list.append(li);
      }
    }
    document.getElementById("limpar").hidden = !data.admin;
  } catch (error) { /* o servidor pode estar reiniciando: tenta de novo daqui a pouco */ }
}
document.getElementById("limpar").onclick = async () => {
  if (!confirm("Limpar todo o ranking do dia?")) return;
  await fetch("/ranking/limpar", { method: "POST" });
  load();
};
load();
setInterval(load, 5000);
</script>
</body></html>
"""


def main() -> None:
    import uvicorn

    lan_url = f"http://{lan_address()}:{PORT}"
    print("=" * 60)
    print(" Mente Financeira • Duelo em sala")
    print(f" Celulares (mesmo Wi-Fi): {lan_url}")
    print(f" Cartaz com QR code:      http://localhost:{PORT}/mesa")
    print(f" Quiz ao vivo (telão):    http://localhost:{PORT}{QUIZ_HOST_PATH}")
    print(f" Sugestões ficam em:     {SUGGESTIONS_FILE}")
    print(" Para encerrar, feche esta janela.")
    print("=" * 60)
    if os.getenv("MENTE_FINANCEIRA_SEM_NAVEGADOR") != "1":
        threading.Timer(2.0, webbrowser.open, (f"http://localhost:{PORT}/mesa",)).start()
    uvicorn.run(create_app(lan_url), host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
