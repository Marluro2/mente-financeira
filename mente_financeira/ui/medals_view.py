"""Medalhas na tela: a janela "Suas medalhas" e o aviso de medalha nova."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import flet as ft

from mente_financeira.core.medals import MEDALS, Medal, MedalBook
from mente_financeira.ui import style as s


def medal_tile(medal: Medal, earned: bool, *, width: float) -> ft.Container:
    """Medalha conquistada em cores; a que falta, apagada e com a meta para conquistar."""

    return ft.Container(
        width=width,
        padding=ft.Padding.symmetric(horizontal=10, vertical=10),
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.18 if earned else 0.06, s.YELLOW if earned else s.WHITE),
        border=ft.Border.all(1.5, s.YELLOW if earned else s.GLASS_BORDER),
        content=ft.Row(
            [
                ft.Container(
                    width=44,
                    height=44,
                    border_radius=22,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=ft.Colors.with_opacity(0.25 if earned else 0.08, s.WHITE),
                    content=ft.Text(medal.emoji, size=24, opacity=1 if earned else 0.3),
                ),
                ft.Column(
                    [
                        ft.Text(medal.title, size=14, weight=ft.FontWeight.W_900, color=s.WHITE if earned else s.MUTED),
                        ft.Text(medal.goal, size=11, color=s.WHITE if earned else s.MUTED),
                    ],
                    spacing=2,
                    expand=True,
                    tight=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def medals_dialog(page: Any, book: MedalBook) -> ft.AlertDialog:
    owned = {medal.key for medal in book.owned()}
    width = min(460, (page.width or 400) - 72)
    columns = 2 if width >= 400 else 1
    tile_width = (width - 10 * (columns - 1)) / columns
    tiles = [medal_tile(medal, medal.key in owned, width=tile_width) for medal in MEDALS]
    dialog = ft.AlertDialog(
        modal=False,
        bgcolor="#2A1A5E",
        title=ft.Row(
            [
                ft.Text("Suas medalhas", weight=ft.FontWeight.W_900, color=s.WHITE, expand=True),
                s.chip(f"{len(owned)} de {len(MEDALS)}", icon=ft.Icons.MILITARY_TECH_ROUNDED, color=s.YELLOW, size=13),
            ]
        ),
        content=ft.Column(
            [
                ft.Text(
                    "Cumpra as metas jogando a memória. As medalhas ficam guardadas só neste aparelho.",
                    size=12,
                    color=s.MUTED,
                ),
                ft.Row(tiles, wrap=True, spacing=10, run_spacing=10, width=width),
            ],
            spacing=12,
            tight=True,
            width=width,
        ),
        scrollable=True,
        actions=[ft.TextButton("Fechar", on_click=lambda _: page.pop_dialog(), style=ft.ButtonStyle(color=s.CYAN))],
    )
    return dialog


def new_medals_block(won: Sequence[Medal]) -> ft.Container:
    """Destaque no resultado da partida: as medalhas que acabaram de chegar."""

    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        border_radius=20,
        gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT, colors=[s.YELLOW, s.ORANGE]),
        content=ft.Column(
            [
                ft.Text(
                    "🏅 Medalha nova!" if len(won) == 1 else f"🏅 {len(won)} medalhas novas!",
                    size=16,
                    weight=ft.FontWeight.W_900,
                    color="#2B1A00",
                    text_align=ft.TextAlign.CENTER,
                ),
                *[
                    ft.Row(
                        [
                            ft.Text(medal.emoji, size=24),
                            ft.Column(
                                [
                                    ft.Text(medal.title, size=14, weight=ft.FontWeight.W_900, color="#2B1A00"),
                                    ft.Text(medal.goal, size=11, color="#4A2E00"),
                                ],
                                spacing=0,
                                tight=True,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    )
                    for medal in won
                ],
            ],
            spacing=6,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )
