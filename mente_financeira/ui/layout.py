"""Faixas de largura de tela e as medidas usadas em cada uma."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

COMPACT_MAX_WIDTH = 700  # celulares em pé
MEDIUM_MAX_WIDTH = 1100  # tablets e janelas estreitas


class Layout(StrEnum):
    COMPACT = "compact"
    MEDIUM = "medium"
    WIDE = "wide"


def layout_for(width: float | None) -> Layout:
    """Escolhe a faixa de layout a partir da largura lógica da página."""

    if width is None or width <= 0:
        return Layout.WIDE  # largura ainda desconhecida: layout de computador
    if width < COMPACT_MAX_WIDTH:
        return Layout.COMPACT
    if width < MEDIUM_MAX_WIDTH:
        return Layout.MEDIUM
    return Layout.WIDE


@dataclass(frozen=True, slots=True)
class Metrics:
    """Tamanhos de fonte e espaçamentos de cada faixa."""

    padding: int
    spacing: int
    question_size: int
    resolution_size: int
    question_lines: int
    label_size: int
    hidden_icon_size: int
    side_title_size: int
    whiteboard_in_sheet: bool  # lousa em painel deslizante em vez de lateral
    icon_only_actions: bool


METRICS: dict[Layout, Metrics] = {
    Layout.COMPACT: Metrics(6, 6, 11, 13, 4, 10, 22, 13, True, True),
    Layout.MEDIUM: Metrics(8, 8, 13, 15, 4, 11, 28, 15, True, False),
    Layout.WIDE: Metrics(10, 8, 12, 15, 3, 11, 30, 15, False, False),
}
