"""Identidade visual da abertura e do Nível 1 (tema escuro com cores neon)."""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

BG_TOP = "#12082E"
BG_MID = "#2A0E61"
BG_BOTTOM = "#4A0C6E"
PINK = "#FF3D8B"
ORANGE = "#FF8A1F"
YELLOW = "#FFD23F"
CYAN = "#3AE0FF"
GREEN = "#2EE59D"
WHITE = "#FFFFFF"
MUTED = "#C9BEF0"
GLASS = "#1AFFFFFF"  # branco com ~10% de opacidade
GLASS_BORDER = "#33FFFFFF"
FRAME = CYAN  # contorno das caixas (tabuleiro, painéis, perguntas)
PANEL = "#2A1A5E"  # fundo das janelas (medalhas, sugestão, avisos)
BOX = "#3A1C8C"  # fundo das caixinhas de resposta
CARD_BACK = "cartas/verso.svg"  # verso das cartas no tema atual


@dataclass(frozen=True, slots=True)
class Theme:
    """Tema de cores escolhido na página inicial: fundo e caixinhas mudam juntos."""

    key: str
    name: str
    background: tuple[str, str, str]  # degradê do fundo (topo, meio, base)
    frame: str
    panel: str
    box: str
    muted: str
    card_back: str


THEMES: tuple[Theme, ...] = (
    Theme("neon", "Roxo Neon", (BG_TOP, BG_MID, BG_BOTTOM), CYAN, PANEL, BOX, MUTED, CARD_BACK),
    Theme("oceano", "Oceano", ("#04122B", "#0A2F5C", "#0B4F7A"), "#3AE0FF", "#102E57", "#174A80", "#BFD9F2", "cartas/temas/verso_oceano.svg"),
    Theme("floresta", "Floresta", ("#061A12", "#0D3B26", "#145A36"), "#B8F35A", "#133D2B", "#1C5A3E", "#C4E8D2", "cartas/temas/verso_floresta.svg"),
    Theme("por_do_sol", "Pôr do Sol", ("#2A0A1E", "#5C1233", "#8A2A1C"), ORANGE, "#4A1530", "#6E2140", "#F2C9CF", "cartas/temas/verso_por_do_sol.svg"),
    Theme("grafite", "Grafite", ("#111317", "#22262E", "#33373F"), YELLOW, "#2A2E36", "#3A3F49", "#C9CDD6", "cartas/temas/verso_grafite.svg"),
)
DEFAULT_THEME = "neon"
theme_key = DEFAULT_THEME


def theme_by_key(key: str) -> Theme:
    return next((t for t in THEMES if t.key == key), THEMES[0])


def apply_theme(key: str) -> Theme:
    """Troca as cores usadas pelas telas. Vale a partir do próximo desenho.

    As cores ficam no módulo, então valem para o processo inteiro. O jogo
    (computador e site) tem um jogador por processo; o servidor da feira nunca
    chama esta função e fica sempre no tema padrão.
    """

    global BG_TOP, BG_MID, BG_BOTTOM, FRAME, PANEL, BOX, MUTED, CARD_BACK, theme_key
    theme = theme_by_key(key)
    BG_TOP, BG_MID, BG_BOTTOM = theme.background
    FRAME, PANEL, BOX, MUTED, CARD_BACK = theme.frame, theme.panel, theme.box, theme.muted, theme.card_back
    theme_key = theme.key
    return theme


def background() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
        colors=[BG_TOP, BG_MID, BG_BOTTOM],
    )


def gradient_text(text: str, size: float, colors: list[str], *, weight: ft.FontWeight = ft.FontWeight.W_900) -> ft.ShaderMask:
    """Texto preenchido com degradê (usado no título)."""

    return ft.ShaderMask(
        content=ft.Text(text, size=size, weight=weight, color=WHITE),
        shader=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT, colors=colors),
        blend_mode=ft.BlendMode.SRC_IN,
    )


def glass(
    content: ft.Control,
    *,
    padding: float = 16,
    radius: float = 22,
    bgcolor: str = GLASS,
    **kwargs,
) -> ft.Container:
    """Painel translúcido ("vidro") sobre o fundo escuro."""

    return ft.Container(
        content=content,
        padding=padding,
        border_radius=radius,
        bgcolor=bgcolor,
        border=ft.Border.all(1, GLASS_BORDER),
        **kwargs,
    )


def pill_button(label: str, icon: ft.IconData, on_click, *, height: float = 58, colors: list[str] | None = None) -> ft.Container:
    """Botão principal em formato de pílula, com degradê e brilho."""

    colors = colors or [PINK, ORANGE]
    return ft.Container(
        height=height,
        border_radius=height / 2,
        gradient=ft.LinearGradient(begin=ft.Alignment.CENTER_LEFT, end=ft.Alignment.CENTER_RIGHT, colors=colors),
        shadow=ft.BoxShadow(blur_radius=28, spread_radius=1, color=ft.Colors.with_opacity(0.55, colors[0]), offset=ft.Offset(0, 8)),
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=on_click,
        content=ft.Row(
            [ft.Icon(icon, color=WHITE, size=26), ft.Text(label, size=19, weight=ft.FontWeight.W_900, color=WHITE)],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
            tight=True,
        ),
    )


def admin_banner(message: str, actions: list[ft.Control] | None = None) -> ft.Container:
    """Faixa amarela exibida em todas as telas no modo administrador."""

    from mente_financeira.admin import ADMIN_COLOR, ADMIN_TEXT_COLOR

    return ft.Container(
        bgcolor=ADMIN_COLOR,
        border_radius=14,
        padding=ft.Padding.symmetric(horizontal=14, vertical=6),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED, color=ADMIN_TEXT_COLOR, size=20),
                ft.Text("MODO ADMINISTRADOR", size=13, weight=ft.FontWeight.W_900, color=ADMIN_TEXT_COLOR),
                ft.Text(message, size=12, color=ADMIN_TEXT_COLOR, expand=True, max_lines=2),
                *(actions or []),
            ],
            spacing=10,
        ),
    )


def chip(text: str, *, icon: ft.IconData | None = None, color: str = CYAN, size: float = 12) -> ft.Container:
    controls: list[ft.Control] = []
    if icon is not None:
        controls.append(ft.Icon(icon, color=color, size=size + 4))
    controls.append(ft.Text(text, size=size, weight=ft.FontWeight.BOLD, color=WHITE))
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        border_radius=20,
        bgcolor=ft.Colors.with_opacity(0.16, color),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.55, color)),
        content=ft.Row(controls, spacing=6, tight=True),
    )


def card_back(src: str) -> str:
    """Verso das cartas: o do baralho no tema padrão, o do tema nos demais."""

    return src if theme_key == DEFAULT_THEME else CARD_BACK
