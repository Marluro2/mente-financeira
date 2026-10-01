"""Modo administrador (para o professor conferir o conteúdo sem jogar).

Como abrir: clique duas vezes em JOGAR_ADMIN.bat (ou no atalho
"Mente Financeira (Administrador)"). O iniciador define MENTE_ADMIN=1.

O que muda no modo administrador:
- faixa amarela "MODO ADMINISTRADOR" nas telas;
- "Painel do professor" na abertura: todos os conceitos do Nível 1 (com dica
  e exemplo), Desafios Relâmpago com gabarito e todas as questões do Nível 2
  com resolução e explicação;
- jogo da memória: botão "Mostrar gabarito" e cronômetro desligado;
- Desafio Relâmpago: o gabarito aparece antes da resposta;
- Nível 2: cronômetro desligado;
- as preferências ficam em uma pasta separada ("admin").
"""

from __future__ import annotations

import os

ADMIN_ENV = "MENTE_ADMIN"
ADMIN_COLOR = "#FFD23F"
ADMIN_TEXT_COLOR = "#2B1A00"


def admin_ativo() -> bool:
    """True quando o jogo foi aberto pelo JOGAR_ADMIN.bat."""

    return os.getenv(ADMIN_ENV, "").strip() == "1"
