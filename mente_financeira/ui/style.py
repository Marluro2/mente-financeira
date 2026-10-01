"""Identidade visual da abertura e do Nível 1 (tema escuro com cores neon)."""

from __future__ import annotations

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
