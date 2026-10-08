"""Gera assets/fontes/emoji.woff2: os emojis do jogo, para funcionar sem internet.

No navegador, o Flet busca os emojis na internet (fonte Noto Color Emoji). Na
feira, sem internet, o servidor da sala (servidor_sala.py) entrega este arquivo
no lugar. Ele traz só os emojis que aparecem no código e nos textos do jogo,
por isso é pequeno. Rode de novo se um emoji novo entrar no jogo:

    pip install fonttools brotli
    python ferramentas/gerar_fonte_emoji.py /caminho/NotoColorEmoji.ttf

A fonte Noto Color Emoji (Google) usa a licença SIL Open Font License 1.1.
"""

from __future__ import annotations

from pathlib import Path
import sys

from fontTools import subset

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "assets" / "fontes" / "emoji.woff2"
EXTRAS = "✅❌👏👍😀😃🙂🤔💪🎮"  # alguns comuns, para textos futuros


def emojis_do_jogo() -> str:
    usados: set[str] = set(EXTRAS)
    for arquivo in [*RAIZ.glob("mente_financeira/**/*.py"), *RAIZ.glob("mente_financeira/**/*.toml")]:
        usados.update(ch for ch in arquivo.read_text(encoding="utf-8") if ord(ch) >= 0x2190)
    return "".join(sorted(usados))


def main(origem: str) -> None:
    opcoes = subset.Options()
    opcoes.flavor = "woff2"
    fonte = subset.load_font(origem, opcoes)
    recorte = subset.Subsetter(opcoes)
    recorte.populate(text=emojis_do_jogo())
    recorte.subset(fonte)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    subset.save_font(fonte, str(SAIDA), opcoes)
    print(f"{SAIDA.relative_to(RAIZ)}: {SAIDA.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")
