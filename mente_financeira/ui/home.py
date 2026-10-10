"""Tela de abertura: título, escolha de modo e acesso aos dois níveis."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from typing import Any

import flet as ft

from mente_financeira.content.memory_deck import MemoryDeck
from mente_financeira.core.medals import MEDALS, MedalBook
from mente_financeira.core.memory_game import Mode
from mente_financeira.ui import style as s
from mente_financeira.ui.layout import Layout, layout_for
from mente_financeira.ui.medals_view import medals_dialog

FLOAT_PERIOD_SECONDS = 2.4

# Ícones que flutuam ao fundo: (ícone, cor, x relativo, y relativo, tamanho).
# São ícones do próprio Flet, e não emojis: aparecem iguais e coloridos em
# qualquer computador, mesmo sem fonte de emoji instalada.
FLOATERS = (
    (ft.Icons.SAVINGS_ROUNDED, s.PINK, 0.05, 0.10, 34),
    (ft.Icons.TRENDING_UP_ROUNDED, s.GREEN, 0.88, 0.09, 32),
    (ft.Icons.CREDIT_CARD_ROUNDED, s.CYAN, 0.04, 0.68, 30),
    (ft.Icons.PERCENT_ROUNDED, s.YELLOW, 0.47, 0.03, 24),
    (ft.Icons.ACCOUNT_BALANCE_ROUNDED, s.ORANGE, 0.74, 0.88, 28),
    (ft.Icons.LIGHTBULB_ROUNDED, s.YELLOW, 0.19, 0.90, 24),
    (ft.Icons.PAID_ROUNDED, s.GREEN, 0.92, 0.60, 34),
)
# No celular o conteúdo ocupa quase toda a tela: só alguns ícones, no topo.
FLOATERS_COMPACT = (
    (ft.Icons.SAVINGS_ROUNDED, s.PINK, 0.04, 0.08, 24),
    (ft.Icons.TRENDING_UP_ROUNDED, s.GREEN, 0.84, 0.08, 22),
    (ft.Icons.PERCENT_ROUNDED, s.YELLOW, 0.84, 0.30, 18),
    (ft.Icons.PAID_ROUNDED, s.CYAN, 0.05, 0.31, 18),
)

# Manchas de luz que derivam devagar ao fundo: (cor, x relativo, y relativo, diâmetro relativo).
ORBS = (
    (s.PINK, -0.10, -0.15, 0.55),
    (s.CYAN, 0.62, 0.45, 0.50),
    ("#8F5BFF", 0.25, 0.70, 0.45),
)

HOVER_SCALE = 1.03



class HomeScreen:
    def __init__(
        self,
        page: ft.Page,
        deck: MemoryDeck,
        *,
        on_play: Callable[[Mode, tuple[str | None, str | None]], None],
        on_level2: Callable[[], None],
        on_admin: Callable[[], None] | None = None,
        on_tracks: Callable[[], None] | None = None,
        medals: MedalBook | None = None,
    ) -> None:
        self.page = page
        self.medals = medals  # botão "Medalhas" no canto (veja medals_view)
        self.deck = deck
        self.on_play = on_play
        self.on_level2 = on_level2
        self.on_admin = on_admin  # só no modo administrador
        self.on_tracks = on_tracks  # volta à página das trilhas
        self.mode = Mode.SOLO
        self.layout = layout_for(page.width)
        self.generation = 0
        self.floaters: list[ft.Container] = []
        self.orbs: list[ft.Container] = []
        self.play_button: ft.Container | None = None
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
        """Dá vida à abertura: ícones flutuam, luzes derivam e o botão pulsa."""

        up = True
        while generation == self.generation:
            for index, floater in enumerate(self.floaters):
                direction = -1 if (index % 2 == 0) == up else 1
                floater.offset = ft.Offset(0, 0.25 * direction)
                floater.rotate = ft.Rotate(math.radians(10 * direction))
            for index, orb in enumerate(self.orbs):
                direction = 1 if (index % 2 == 0) == up else -1
                orb.offset = ft.Offset(0.08 * direction, 0.06 * direction)
            if self.play_button is not None:
                self.play_button.scale = 1.04 if up else 1.0
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
        motion = ft.Animation(int(FLOAT_PERIOD_SECONDS * 1000), ft.AnimationCurve.EASE_IN_OUT)
        self.floaters = [
            self._floater(icon, color, size, left=x * width, top=y * height, motion=motion)
            for icon, color, x, y, size in (FLOATERS_COMPACT if self.compact else FLOATERS)
        ]
        self.orbs = [
            ft.Container(
                left=x * width,
                top=y * height,
                width=diameter * max(width, height),
                height=diameter * max(width, height),
                shape=ft.BoxShape.CIRCLE,
                gradient=ft.RadialGradient(
                    colors=[ft.Colors.with_opacity(0.32, color), ft.Colors.with_opacity(0, color)],
                ),
                offset=ft.Offset(0, 0),
                animate_offset=ft.Animation(int(FLOAT_PERIOD_SECONDS * 2000), ft.AnimationCurve.EASE_IN_OUT),
            )
            for color, x, y, diameter in ORBS
        ]
        content = self._panel_content()
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                gradient=s.background(),
                content=ft.Stack(
                    [
                        *self.orbs,
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
                        *self._back_button(),
                        *self._medals_button(),
                    ],
                    expand=True,
                ),
            ),
        )

    def _panel_content(self) -> ft.Control:
        """Painel central de vidro: título, escolha de modo, nome e botão de jogar."""

        items: list[ft.Control] = [
            self._title(),
            ft.Text(
                "Como você quer jogar?",
                size=20 if self.compact else 24,
                weight=ft.FontWeight.W_900,
                color=s.WHITE,
                text_align=ft.TextAlign.CENTER,
            ),
            self._mode_picker(),
            self._names(),
            self._play_button(height=58 if self.compact or self.short else 66),
        ]
        if self.on_admin:
            items.insert(0, self._admin_banner())
            items.append(self._admin_card())
        panel = ft.Container(
            width=None if self.compact else 600,
            padding=ft.Padding.symmetric(horizontal=12, vertical=24) if self.compact else (24 if self.short else 32),
            border_radius=28 if self.compact else 32,
            bgcolor=ft.Colors.with_opacity(0.10, s.WHITE),
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.35, s.CYAN)),
            shadow=ft.BoxShadow(blur_radius=60, color=ft.Colors.with_opacity(0.35, "#6C63FF")),
            content=ft.Column(
                items,
                spacing=14 if self.compact or self.short else 18,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )
        # Espaço no topo para o botão "Trilhas", que fica no canto da tela.
        top = 64 if self.on_tracks is not None else 16
        return ft.Container(
            padding=ft.Padding.only(left=12, right=12, top=top, bottom=16) if self.compact else ft.Padding.symmetric(horizontal=32, vertical=top),
            content=panel,
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
    def _back_button(self) -> list[ft.Control]:
        """Botão "Trilhas", grande, no canto superior esquerdo (só dentro de uma trilha)."""

        if self.on_tracks is None:
            return []
        return [
            ft.Container(
                left=8,
                top=8,
                content=ft.TextButton(
                    "Trilhas",
                    icon=ft.Icons.ARROW_BACK_ROUNDED,
                    on_click=self._back_to_tracks,
                    style=ft.ButtonStyle(
                        color=s.CYAN,
                        icon_size=30 if self.compact else 36,
                        text_style=ft.TextStyle(size=22 if self.compact else 28, weight=ft.FontWeight.W_900),
                        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                    ),
                ),
            )
        ]

    def _medals_button(self) -> list[ft.Control]:
        """Botão "Medalhas", no canto superior direito, com quantas já foram conquistadas."""

        if self.medals is None:
            return []
        count = f"{len(self.medals.owned())}/{len(MEDALS)}"
        return [
            ft.Container(
                right=8,
                top=8,
                content=ft.TextButton(
                    count if self.compact else f"Medalhas {count}",
                    icon=ft.Icons.MILITARY_TECH_ROUNDED,
                    on_click=self._open_medals,
                    tooltip="Suas medalhas",
                    style=ft.ButtonStyle(
                        color=s.YELLOW,
                        icon_size=30 if self.compact else 34,
                        text_style=ft.TextStyle(size=20 if self.compact else 24, weight=ft.FontWeight.W_900),
                        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                    ),
                ),
            )
        ]

    def _open_medals(self, _: Any = None) -> None:
        if self.medals is not None:
            self.page.show_dialog(medals_dialog(self.page, self.medals))

    def _back_to_tracks(self, _: Any = None) -> None:
        self.stop()
        if self.on_tracks is not None:
            self.on_tracks()

    def _title(self) -> ft.Control:
        big, small = (50, 34) if self.compact else ((62, 40) if self.short else (78, 50))
        align = ft.CrossAxisAlignment.CENTER
        return ft.Column(
            [
                s.gradient_text("MENTE", big, [s.YELLOW, s.ORANGE, s.PINK]),
                s.gradient_text("FINANCEIRA", small, [s.CYAN, "#8F88FF", s.PINK]),
            ],
            spacing=0,
            horizontal_alignment=align,
        )

    def _mode_tile(self, mode: Mode, icon: ft.IconData, title: str, subtitle: str) -> ft.Container:
        selected = self.mode is mode
        if selected:
            look: dict[str, Any] = {
                "gradient": ft.LinearGradient(
                    begin=ft.Alignment.TOP_LEFT,
                    end=ft.Alignment.BOTTOM_RIGHT,
                    colors=[ft.Colors.with_opacity(0.40, s.CYAN), ft.Colors.with_opacity(0.30, "#6C63FF")],
                ),
                "border": ft.Border.all(2, s.CYAN),
                "shadow": ft.BoxShadow(blur_radius=26, color=ft.Colors.with_opacity(0.45, s.CYAN), offset=ft.Offset(0, 6)),
            }
        else:
            look = {
                "bgcolor": ft.Colors.with_opacity(0.08, s.WHITE),
                "border": ft.Border.all(1, s.GLASS_BORDER),
            }
        tile = ft.Column(
            [
                ft.Container(
                    width=46,
                    height=46,
                    border_radius=23,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=ft.Colors.with_opacity(0.25 if selected else 0.10, s.CYAN if selected else s.WHITE),
                    content=ft.Icon(icon, color=s.WHITE if selected else s.MUTED, size=26),
                ),
                ft.Text(title, size=17, weight=ft.FontWeight.W_900, color=s.WHITE),
                ft.Text(subtitle, size=12, color=s.WHITE if selected else s.MUTED),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        badge = ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=s.CYAN, size=22, visible=selected)
        return ft.Container(
            expand=True,
            padding=10 if self.short else 14,
            border_radius=20,
            ink=True,
            data=mode,
            on_click=self._select_mode,
            on_hover=self._hover,
            scale=1,
            animate_scale=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            content=ft.Stack([ft.Row([tile], alignment=ft.MainAxisAlignment.CENTER), ft.Container(badge, right=0, top=0)]),
            **look,
        )

    def _mode_picker(self) -> ft.Control:
        return ft.Row(
            [
                self._mode_tile(Mode.SOLO, ft.Icons.PERSON_ROUNDED, "Solo", "Relógio + desafios"),
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

    # ------------------------------------------------------------ animações
    def _floater(
        self, icon: ft.IconData, color: str, size: float, *, left: float, top: float, motion: ft.Animation
    ) -> ft.Container:
        """Ícone em uma bolha de vidro com brilho colorido, que flutua ao fundo."""

        bubble = size * 1.9
        return ft.Container(
            left=left,
            top=top,
            width=bubble,
            height=bubble,
            border_radius=bubble / 2,
            alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.with_opacity(0.14, color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.45, color)),
            shadow=ft.BoxShadow(blur_radius=24, color=ft.Colors.with_opacity(0.45, color)),
            opacity=0.55 if self.compact else 0.8,
            content=ft.Icon(icon, color=color, size=size),
            offset=ft.Offset(0, 0),
            rotate=ft.Rotate(0),
            animate_offset=motion,
            animate_rotation=motion,
        )

    def _play_button(self, *, height: float = 58) -> ft.Container:
        """Botão principal, que pulsa devagar para chamar a atenção."""

        self.play_button = s.pill_button("JOGAR AGORA", ft.Icons.PLAY_ARROW_ROUNDED, self._play, height=height)
        self.play_button.scale = 1
        self.play_button.animate_scale = ft.Animation(int(FLOAT_PERIOD_SECONDS * 1000), ft.AnimationCurve.EASE_IN_OUT)
        return self.play_button

    def _hover(self, event: Any) -> None:
        """Cartões crescem um pouco quando o mouse passa por cima."""

        hovered = event.data in (True, "true")
        event.control.scale = HOVER_SCALE if hovered else 1
        event.control.update()

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
