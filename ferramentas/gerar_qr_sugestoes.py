"""Gera assets/qr/sugestoes.png: QR code do Formulário Google de sugestões.

O site não tem como desenhar QR codes, então a imagem fica pronta em assets.
Rode de novo se o endereço (FORM_URL em mente_financeira/sugestoes.py) mudar:

    pip install segno
    python ferramentas/gerar_qr_sugestoes.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import segno

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from mente_financeira.sugestoes import FORM_URL  # noqa: E402

SAIDA = RAIZ / "assets" / "qr" / "sugestoes.png"


def main() -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    segno.make(FORM_URL, error="m").save(SAIDA, kind="png", scale=10, border=2, dark="#12082E")
    print(f"{SAIDA.relative_to(RAIZ)} -> {FORM_URL}")


if __name__ == "__main__":
    main()
