"""Página inicial: escolha da trilha educacional.

As trilhas seguem o Quadro 2 do projeto: Ensino Fundamental 1 e 2, Ensino
Médio e Engenharia de Produção. À esquerda ficam os botões; à direita, um
tabuleiro de cartas "vivo" (reto e alinhado), em que uma carta vira de tempos em tempos e mostra
um conceito do jogo.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import random
from typing import Any

import flet as ft

from mente_financeira.content.memory_deck import MemoryDeck
from mente_financeira.ui import style as s
from mente_financeira.ui.suggestion_form import suggestion_button, suggestion_qr_tile
from mente_financeira.ui.layout import Layout, layout_for

FLIP_PERIOD_SECONDS = 1.6
BOARD_COLUMNS = 4

FUNDAMENTAL_1, FUNDAMENTAL, MEDIO, ENGENHARIA = "fundamental1", "fundamental", "medio", "engenharia"


@dataclass(frozen=True, slots=True)
class TrackOption:
    key: str
    title: str
    subtitle: str
    icon: ft.IconData
    colors: tuple[str, str]
    available: bool


TRACKS: tuple[TrackOption, ...] = (
    TrackOption(
        FUNDAMENTAL_1,
        "Ensino Fundamental 1",
        "Dinheiro, troco, compras e primeiras economias",
        ft.Icons.TOYS_ROUNDED,
        (s.YELLOW, s.ORANGE),
        available=True,
    ),
    TrackOption(
        FUNDAMENTAL,
        "Ensino Fundamental 2",
        "Porcentagem, consumo e primeiros conceitos",
        ft.Icons.BACKPACK_ROUNDED,
        (s.PINK, s.ORANGE),
        available=True,
    ),
    TrackOption(
        MEDIO,
        "Ensino Médio",
        "Juros, inflação, crédito e financiamentos",
        ft.Icons.MENU_BOOK_ROUNDED,
        (s.CYAN, "#6C63FF"),
        available=False,
    ),
    TrackOption(
        ENGENHARIA,
        "Engenharia de Produção",
        "Fluxo de caixa, VPL, TIR e análise de investimentos",
        ft.Icons.PRECISION_MANUFACTURING_ROUNDED,
        (s.GREEN, "#0B9486"),
        available=False,
    ),
)


class TracksScreen:
    def __init__(
        self,
        page: ft.Page,
        deck: MemoryDeck,
        *,
        on_select: Callable[[str], None],
        rng: random.Random | None = None,
        suggest_url: str | None = None,
    ) -> None:
        self.page = page
        self.deck = deck
        self.on_select = on_select
        self.suggest_url = suggest_url  # Formulário Google de sugestões (sem ele, nada aparece)
        self.rng = rng or random.Random()
        self.layout = layout_for(page.width)
        self.generation = 0
        self.rendered_size: tuple[float, float] = (0, 0)
        self.switchers: list[ft.AnimatedSwitcher] = []
        self.card_size = 100.0
        self.open_card: int | None = None

    # ------------------------------------------------------------ ciclo
    def show(self) -> None:
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = s.BG_TOP
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()
        self.generation += 1
        self.page.run_task(self._flip_loop, self.generation)

    def stop(self) -> None:
        self.generation += 1

    def on_resize(self, event: Any) -> None:
        # O tabuleiro acompanha o tamanho da janela.
        size = (self.page.width or 0, self.page.height or 0)
        self.layout = layout_for(getattr(event, "width", None) or self.page.width)
        if size != self.rendered_size:
            self.show()

    async def _flip_loop(self, generation: int) -> None:
        """Vira uma carta por vez, como uma prévia do jogo."""

        while generation == self.generation:
            await asyncio.sleep(FLIP_PERIOD_SECONDS)
            if generation != self.generation or not self.switchers:
                return
            if self.open_card is not None:
                self.switchers[self.open_card].content = self._back(self.open_card)
            self.open_card = self.rng.randrange(len(self.switchers))
            concept = self.rng.choice(self.deck.concepts)
            self.switchers[self.open_card].content = ft.Image(
                key=f"frente-{self.open_card}-{concept.id}",
                src=concept.image,
                width=self.card_size,
                height=self.card_size,
                fit=ft.BoxFit.COVER,
                semantics_label=concept.name,
            )
            self.page.update()

    # ------------------------------------------------------------ desenho
    @property
    def compact(self) -> bool:
        return self.layout is Layout.COMPACT

    def build(self) -> ft.Control:
        width = self.page.width or 1280
        height = self.page.height or 720
        self.rendered_size = (self.page.width or 0, self.page.height or 0)
        short = height < 900

        title = ft.Column(
            [
                s.gradient_text("MENTE", 44 if self.compact else (58 if short else 72), [s.YELLOW, s.ORANGE, s.PINK]),
                s.gradient_text("FINANCEIRA", 30 if self.compact else (38 if short else 46), [s.CYAN, "#8F88FF", s.PINK]),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER if self.compact else ft.CrossAxisAlignment.START,
        )
        heading = ft.Text(
            "Qual é a sua trilha?",
            size=20 if self.compact else 24,
            weight=ft.FontWeight.W_900,
            color=s.WHITE,
            text_align=ft.TextAlign.CENTER if self.compact else ft.TextAlign.START,
        )
        badge = ft.Row(
            [s.chip("PROJETO IFSP • EDUCAÇÃO FINANCEIRA", icon=ft.Icons.AUTO_AWESOME, color=s.YELLOW, size=11)],
            alignment=ft.MainAxisAlignment.CENTER if self.compact else ft.MainAxisAlignment.START,
        )
        buttons = ft.Column([self._track_button(track) for track in TRACKS], spacing=12 if short else 16)
        footer = ft.Text(
            "Um jogo, quatro trilhas: das primeiras contas com dinheiro à análise de investimentos.",
            size=12,
            color=s.MUTED,
            text_align=ft.TextAlign.CENTER if self.compact else ft.TextAlign.START,
        )
        if self.suggest_url:
            # QR do formulário ao lado do título; o botão continua no rodapé.
            qr = suggestion_qr_tile(self.suggest_url, size=72 if self.compact else (96 if short else 112))
            title = ft.Row(
                [title, qr],
                spacing=16 if self.compact else 28,
                alignment=ft.MainAxisAlignment.CENTER if self.compact else ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            suggest = ft.Row(
                [suggestion_button(url=self.suggest_url)],
                alignment=ft.MainAxisAlignment.CENTER if self.compact else ft.MainAxisAlignment.START,
            )
            footer = ft.Column([footer, suggest], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        if self.compact:
            board = self._board(side=min(width - 40, 340), rows=2)
            content: ft.Control = ft.Container(
                padding=ft.Padding.symmetric(horizontal=18, vertical=20),
                content=ft.Column(
                    [badge, title, heading, buttons, ft.Row([board], alignment=ft.MainAxisAlignment.CENTER), footer],
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            )
        else:
            left_width = 480
            side = max(280, min(height - 120, width - left_width - 180, 600))
            left = ft.Column([badge, title, heading, buttons, footer], spacing=14 if short else 20, width=left_width)
            content = ft.Container(
                padding=ft.Padding.symmetric(horizontal=32, vertical=12 if short else 28),
                content=ft.Row(
                    [left, self._board(side=side, rows=4)],
                    spacing=64,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                gradient=s.background(),
                content=ft.Column(
                    [content],
                    scroll=ft.ScrollMode.AUTO,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )

    def _track_button(self, track: TrackOption) -> ft.Container:
        first, second = track.colors
        if track.available:
            decoration: dict[str, Any] = {
                "gradient": ft.LinearGradient(begin=ft.Alignment.CENTER_LEFT, end=ft.Alignment.CENTER_RIGHT, colors=[first, second]),
                "shadow": ft.BoxShadow(blur_radius=28, spread_radius=1, color=ft.Colors.with_opacity(0.5, first), offset=ft.Offset(0, 8)),
            }
            trailing: ft.Control = ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=s.WHITE, size=28)
            icon_bg, text_color, sub_color = ft.Colors.with_opacity(0.25, s.WHITE), s.WHITE, s.WHITE
        else:
            decoration = {
                "bgcolor": ft.Colors.with_opacity(0.10, first),
                "border": ft.Border.all(1.5, ft.Colors.with_opacity(0.55, first)),
            }
            trailing = s.chip("EM BREVE", icon=ft.Icons.LOCK_CLOCK_ROUNDED, color=first, size=11)
            icon_bg, text_color, sub_color = ft.Colors.with_opacity(0.18, first), s.WHITE, s.MUTED
        below = self.compact and not track.available
        return ft.Container(
            data=track.key,
            on_click=self._choose,
            ink=True,
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            border_radius=24,
            content=ft.Row(
                [
                    ft.Container(
                        width=54,
                        height=54,
                        border_radius=18,
                        bgcolor=icon_bg,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(track.icon, color=s.WHITE if track.available else first, size=30),
                    ),
                    ft.Column(
                        [
                            ft.Text(track.title, size=18 if self.compact else 21, weight=ft.FontWeight.W_900, color=text_color),
                            ft.Text(track.subtitle, size=12 if self.compact else 13, color=sub_color),
                            # No celular a etiqueta "EM BREVE" vai para baixo do texto,
                            # para o título caber numa linha.
                            *([trailing] if below else []),
                        ],
                        spacing=1 if not below else 6,
                        expand=True,
                    ),
                    *([] if below else [trailing]),
                ],
                spacing=14,
            ),
            **decoration,
        )

    def _back(self, index: int) -> ft.Image:
        return ft.Image(
            key=f"verso-{index}",
            src=self.deck.back_image,
            width=self.card_size,
            height=self.card_size,
            fit=ft.BoxFit.COVER,
            semantics_label="Carta Mente Financeira",
        )

    def _board(self, *, side: float, rows: int) -> ft.Control:
        """Tabuleiro decorativo, reto e alinhado, com cartas que viram."""

        gap = 8 if self.compact else 12
        self.card_size = (side - (BOARD_COLUMNS - 1) * gap) / BOARD_COLUMNS
        self.switchers = []
        self.open_card = None
        lines: list[ft.Control] = []
        for row in range(rows):
            cards: list[ft.Control] = []
            for col in range(BOARD_COLUMNS):
                index = row * BOARD_COLUMNS + col
                switcher = ft.AnimatedSwitcher(
                    content=self._back(index),
                    transition=ft.AnimatedSwitcherTransition.SCALE,
                    duration=320,
                    reverse_duration=220,
                    switch_in_curve=ft.AnimationCurve.EASE_OUT_BACK,
                    switch_out_curve=ft.AnimationCurve.EASE_IN,
                )
                self.switchers.append(switcher)
                cards.append(
                    ft.Container(
                        width=self.card_size,
                        height=self.card_size,
                        border_radius=self.card_size * 0.18,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        shadow=ft.BoxShadow(blur_radius=14, color="#66000000", offset=ft.Offset(0, 6)),
                        content=switcher,
                    )
                )
            lines.append(ft.Row(cards, spacing=gap, tight=True))
        return ft.Container(
            padding=gap + 6,
            border_radius=32,
            bgcolor=ft.Colors.with_opacity(0.08, s.WHITE),
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.5, s.CYAN)),
            shadow=ft.BoxShadow(blur_radius=50, color=ft.Colors.with_opacity(0.35, s.CYAN)),
            content=ft.Column(lines, spacing=gap, tight=True),
        )

    # ------------------------------------------------------------ ações
    def _choose(self, event: Any) -> None:
        track = next(t for t in TRACKS if t.key == event.control.data)
        if track.available:
            self.stop()
            self.on_select(track.key)
            return
        self.page.show_dialog(
            ft.SnackBar(
                ft.Text(f"A trilha {track.title} está em construção. Em breve! 🚧", color=s.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor="#E63A1C9C",
                behavior=ft.SnackBarBehavior.FLOATING,
                duration=2200,
            )
        )
