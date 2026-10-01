"""Tela de abertura: título, escolha de modo e acesso aos dois níveis."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from typing import Any

import flet as ft

from mente_financeira.content.memory_deck import MemoryDeck
from mente_financeira.core.memory_game import Mode
from mente_financeira.ui import style as s
from mente_financeira.ui.layout import Layout, layout_for

FLOAT_PERIOD_SECONDS = 2.4

# Ícones que flutuam ao fundo: (emoji, x relativo, y relativo, tamanho).
FLOATERS = (
    ("💰", 0.06, 0.10, 44),
    ("📈", 0.86, 0.08, 40),
    ("🐷", 0.90, 0.62, 46),
    ("💳", 0.04, 0.70, 38),
    ("🎯", 0.48, 0.03, 30),
    ("🪙", 0.72, 0.88, 34),
    ("💡", 0.20, 0.92, 30),
)
# No celular o conteúdo ocupa quase toda a tela: só alguns ícones, no topo.
FLOATERS_COMPACT = (
    ("💰", 0.04, 0.09, 34),
    ("📈", 0.86, 0.09, 32),
    ("🎯", 0.84, 0.30, 26),
    ("🪙", 0.05, 0.31, 26),
)

# Cartas exibidas em leque na abertura: (id do conceito, ângulo em graus).
FAN = (("poupanca", -14), ("investimento", 0), ("cartao_credito", 14))


class HomeScreen:
    def __init__(
        self,
        page: ft.Page,
        deck: MemoryDeck,
        *,
        on_play: Callable[[Mode, tuple[str | None, str | None]], None],
        on_level2: Callable[[], None],
        on_admin: Callable[[], None] | None = None,
    ) -> None:
        self.page = page
        self.deck = deck
        self.on_play = on_play
        self.on_level2 = on_level2
        self.on_admin = on_admin  # só no modo administrador
        self.mode = Mode.SOLO
        self.layout = layout_for(page.width)
        self.generation = 0
        self.floaters: list[ft.Container] = []
        self.name_1 = ft.TextField()
        self.name_2 = ft.TextField()
        self.rendered_short = False

    # ------------------------------------------------------------ ciclo
    def show(self) -> None:
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = s.BG_TOP
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()
        self.generation += 1
        self.page.run_task(self._float_loop, self.generation)

    def stop(self) -> None:
        self.generation += 1

    def on_resize(self, event: Any) -> None:
        new_layout = layout_for(getattr(event, "width", None) or self.page.width)
        if new_layout is not self.layout or self.short != self.rendered_short:
            self.layout = new_layout
            self.show()

    async def _float_loop(self, generation: int) -> None:
        """Faz os ícones do fundo subirem e descerem suavemente."""

        up = True
        while generation == self.generation:
            for index, floater in enumerate(self.floaters):
                direction = -1 if (index % 2 == 0) == up else 1
                floater.offset = ft.Offset(0, 0.25 * direction)
            up = not up
            self.page.update()
            await asyncio.sleep(FLOAT_PERIOD_SECONDS)

    # ------------------------------------------------------------ desenho
    @property
    def compact(self) -> bool:
        return self.layout is Layout.COMPACT

    @property
    def short(self) -> bool:
        """Computador com tela baixa (ex.: notebook 1536×864 com barra de tarefas)."""

        return not self.compact and (self.page.height or 800) < 900

    def build(self) -> ft.Control:
        self.rendered_short = self.short  # para saber se a altura mudou de faixa
        width = self.page.width or 1280
        height = self.page.height or 720
        self.floaters = [
            ft.Container(
                content=ft.Text(emoji, size=size),
                left=x * width,
                top=y * height,
                opacity=0.25 if self.compact else 0.35,
                offset=ft.Offset(0, 0),
                animate_offset=ft.Animation(int(FLOAT_PERIOD_SECONDS * 1000), ft.AnimationCurve.EASE_IN_OUT),
            )
            for emoji, x, y, size in (FLOATERS_COMPACT if self.compact else FLOATERS)
        ]
        content = self._compact_content() if self.compact else self._wide_content()
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                gradient=s.background(),
                content=ft.Stack(
                    [
                        *self.floaters,
                        # Posicionado nas quatro bordas: ocupa toda a pilha.
                        ft.Container(
                            left=0,
                            top=0,
                            right=0,
                            bottom=0,
                            content=ft.Column(
                                [content],
                                scroll=ft.ScrollMode.AUTO,
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ),
                    ],
                    expand=True,
                ),
            ),
        )

    def _compact_content(self) -> ft.Control:
        items: list[ft.Control] = [
            self._badge(),
            self._fan(card=92),
            self._title(),
            self._tagline(),
            self._mode_picker(),
            self._names(),
            s.pill_button("JOGAR AGORA", ft.Icons.PLAY_ARROW_ROUNDED, self._play),
            self._level2_card(),
            self._footer(),
        ]
        if self.on_admin:
            items.insert(0, self._admin_banner())
            items.insert(-1, self._admin_card())
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=18, vertical=22),
            content=ft.Column(items, spacing=18, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        )

    def _wide_content(self) -> ft.Control:
        left = ft.Column(
            [
                self._badge(),
                self._title(),
                self._tagline(),
                self._mode_picker(),
                self._names(),
                s.pill_button("JOGAR AGORA", ft.Icons.PLAY_ARROW_ROUNDED, self._play, height=54 if self.short else 62),
            ],
            spacing=12 if self.short else 20,
            width=470,
        )
        right_items: list[ft.Control] = [self._fan(card=130 if self.short else 150), self._level2_card(), self._footer()]
        if self.on_admin:
            right_items.insert(2, self._admin_card())
        right = ft.Column(
            right_items,
            spacing=26,
            width=400,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        row = ft.Row(
            [left, right],
            spacing=56,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        content: ft.Control = row
        if self.on_admin:
            content = ft.Column(
                [ft.Container(self._admin_banner(), width=470 + 56 + 400), row],
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=32, vertical=10 if self.short else 28), content=content
        )

    def _admin_banner(self) -> ft.Control:
        return s.admin_banner("Cronômetro desligado, gabaritos visíveis e preferências separadas.")

    def _admin_card(self) -> ft.Control:
        return ft.Container(
            ink=True,
            on_click=lambda _: self.on_admin(),
            padding=14,
            border_radius=22,
            bgcolor=ft.Colors.with_opacity(0.18, s.YELLOW),
            border=ft.Border.all(2, s.YELLOW),
            content=ft.Row(
                [
                    ft.Container(
                        width=52,
                        height=52,
                        border_radius=16,
                        bgcolor=s.YELLOW,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED, color="#2B1A00", size=30),
                    ),
                    ft.Column(
                        [
                            ft.Text("ADMINISTRADOR", size=11, weight=ft.FontWeight.BOLD, color=s.YELLOW),
                            ft.Text("Painel do professor", size=17, weight=ft.FontWeight.W_900, color=s.WHITE),
                            ft.Text("Conceitos, desafios e questões com gabarito.", size=12, color=s.MUTED),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=s.YELLOW),
                ],
                spacing=14,
            ),
        )

    # ------------------------------------------------------------ peças
    def _badge(self) -> ft.Control:
        return ft.Row(
            [s.chip("PROJETO IFSP • EDUCAÇÃO FINANCEIRA", icon=ft.Icons.AUTO_AWESOME, color=s.YELLOW, size=11)],
            alignment=ft.MainAxisAlignment.CENTER if self.compact else ft.MainAxisAlignment.START,
        )

    def _title(self) -> ft.Control:
        big, small = (50, 34) if self.compact else ((62, 40) if self.short else (78, 50))
        align = ft.CrossAxisAlignment.CENTER if self.compact else ft.CrossAxisAlignment.START
        return ft.Column(
            [
                s.gradient_text("MENTE", big, [s.YELLOW, s.ORANGE, s.PINK]),
                s.gradient_text("FINANCEIRA", small, [s.CYAN, "#8F88FF", s.PINK]),
            ],
            spacing=0,
            horizontal_alignment=align,
        )

    def _tagline(self) -> ft.Control:
        return ft.Text(
            "Vire as cartas, forme os pares e descubra os segredos do dinheiro. 💸",
            size=16 if self.compact else 19,
            color=s.MUTED,
            text_align=ft.TextAlign.CENTER if self.compact else ft.TextAlign.START,
        )

    def _fan(self, *, card: float) -> ft.Control:
        concepts = {concept.id: concept for concept in self.deck.concepts}
        width = card * 2.3
        items: list[ft.Control] = []
        for position, (concept_id, degrees) in enumerate(FAN):
            concept = concepts.get(concept_id)
            if concept is None:
                continue
            items.append(
                ft.Container(
                    left=(width - card) / 2 + (position - 1) * card * 0.62,
                    top=card * 0.12 if position != 1 else 0,
                    width=card,
                    height=card,
                    rotate=ft.Rotate(math.radians(degrees)),
                    border_radius=card * 0.18,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    shadow=ft.BoxShadow(blur_radius=24, color="#66000000", offset=ft.Offset(0, 10)),
                    content=ft.Image(src=concept.image, fit=ft.BoxFit.COVER, semantics_label=concept.name),
                )
            )
        return ft.Row(
            [ft.Stack(items, width=width, height=card * 1.25)],
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _mode_tile(self, mode: Mode, icon: ft.IconData, title: str, subtitle: str) -> ft.Container:
        selected = self.mode is mode
        return ft.Container(
            expand=True,
            padding=10 if self.short else 14,
            border_radius=18,
            bgcolor=ft.Colors.with_opacity(0.22 if selected else 0.08, s.CYAN if selected else s.WHITE),
            border=ft.Border.all(2 if selected else 1, s.CYAN if selected else s.GLASS_BORDER),
            ink=True,
            data=mode,
            on_click=self._select_mode,
            content=ft.Column(
                [
                    ft.Icon(icon, color=s.CYAN if selected else s.MUTED, size=28),
                    ft.Text(title, size=17, weight=ft.FontWeight.W_900, color=s.WHITE),
                    ft.Text(subtitle, size=12, color=s.MUTED),
                ],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _mode_picker(self) -> ft.Control:
        return ft.Row(
            [
                self._mode_tile(Mode.SOLO, ft.Icons.PERSON_ROUNDED, "Solo", "Contra o relógio"),
                self._mode_tile(Mode.DUEL, ft.Icons.PEOPLE_ALT_ROUNDED, "Duelo", "2 jogadores + desafios"),
            ],
            spacing=12,
        )

    def _name_field(self, label: str, value: str | None, *, in_row: bool) -> ft.TextField:
        # expand só dentro de linhas: numa coluna rolável ele quebraria a tela.
        return ft.TextField(
            value=value,
            label=label,
            max_length=24,
            border_radius=16,
            filled=True,
            bgcolor=ft.Colors.with_opacity(0.10, s.WHITE),
            border_color=s.GLASS_BORDER,
            focused_border_color=s.CYAN,
            color=s.WHITE,
            label_style=ft.TextStyle(color=s.MUTED),
            prefix_icon=ft.Icons.BADGE_OUTLINED,
            expand=in_row,
            on_submit=self._play,
        )

    def _names(self) -> ft.Control:
        first, second = self.name_1.value, self.name_2.value
        if self.mode is Mode.SOLO:
            self.name_1 = self._name_field("Seu nome (opcional)", first, in_row=True)
            return ft.Row([self.name_1])
        in_row = not self.compact
        self.name_1 = self._name_field("Jogador 1", first, in_row=in_row)
        self.name_2 = self._name_field("Jogador 2", second, in_row=in_row)
        if self.compact:
            return ft.Column([self.name_1, self.name_2], spacing=10)
        return ft.Row([self.name_1, self.name_2], spacing=12)

    def _level2_card(self) -> ft.Control:
        return s.glass(
            ft.Row(
                [
                    ft.Container(
                        width=52,
                        height=52,
                        border_radius=16,
                        gradient=ft.LinearGradient(colors=[s.CYAN, "#6C63FF"]),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.CALCULATE_ROUNDED, color=s.WHITE, size=28),
                    ),
                    ft.Column(
                        [
                            ft.Text("NÍVEL 2", size=11, weight=ft.FontWeight.BOLD, color=s.CYAN),
                            ft.Text("Desafio dos Cálculos", size=17, weight=ft.FontWeight.W_900, color=s.WHITE),
                            ft.Text("Porcentagem, juros e financiamentos.", size=12, color=s.MUTED),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    ft.IconButton(
                        ft.Icons.ARROW_FORWARD_ROUNDED,
                        icon_color=s.WHITE,
                        tooltip="Entrar no Nível 2",
                        on_click=lambda _: self.on_level2(),
                        style=ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.18, s.CYAN)),
                    ),
                ],
                spacing=14,
            ),
            padding=14,
            ink=True,
            on_click=lambda _: self.on_level2(),
        )

    def _footer(self) -> ft.Control:
        total = len(self.deck.concepts)
        return ft.Text(
            f"🃏 {self.deck.pairs * 2} cartas  •  💡 {total} conceitos  •  🎮 1 ou 2 jogadores",
            size=12,
            color=s.MUTED,
            text_align=ft.TextAlign.CENTER,
        )

    # ------------------------------------------------------------ ações
    def _select_mode(self, event: Any) -> None:
        mode = event.control.data
        if mode is self.mode:
            return
        self.mode = mode
        self.show()

    def _play(self, _: Any = None) -> None:
        names = (self.name_1.value, self.name_2.value if self.mode is Mode.DUEL else None)
        self.stop()
        self.on_play(self.mode, names)
