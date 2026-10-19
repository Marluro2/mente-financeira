"""Escolha do nível da trilha de Engenharia de Produção.

Fica entre a página das trilhas e a abertura do jogo (Solo ou Duelo). À
esquerda, uma caixa por nível; à direita, um quadro com os conteúdos da trilha
flutuando. Passar o mouse num nível destaca os conteúdos dele; no celular, sem
mouse, o destaque passa sozinho de um nível para o outro. Os três níveis ficam
abertos desde o começo.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import random
from typing import Any

import flet as ft

from mente_financeira.ui import style as s
from mente_financeira.ui.layout import Layout, layout_for

FLOAT_PERIOD_SECONDS = 2.4
AUTO_HIGHLIGHT_TICKS = 2  # no celular, o destaque troca de nível a cada 2 balanços
HOVER_SCALE = 1.03
HIGHLIGHT_SCALE = 1.15


@dataclass(frozen=True, slots=True)
class Level:
    key: str
    number: int
    title: str
    subtitle: str
    icon: ft.IconData
    color: str
    topics: tuple[str, ...]  # conteúdos que acendem no quadro


LEVELS: tuple[Level, ...] = (
    Level(
        "nivel1",
        1,
        "Fundamentos financeiros e de custos",
        "Fluxo de caixa, custos e ponto de equilíbrio",
        ft.Icons.CALCULATE_ROUNDED,
        s.GREEN,
        ("Fluxo de caixa", "Custos", "Ponto de equilíbrio", "Margem de contribuição", "Depreciação", "Valor presente"),
    ),
    Level(
        "nivel2",
        2,
        "Avaliação de investimentos",
        "TIR, VPL, payback e financiamentos",
        ft.Icons.TRENDING_UP_ROUNDED,
        s.CYAN,
        ("TIR", "VPL", "Payback", "TMA", "SAC e Price"),
    ),
    Level(
        "nivel3",
        3,
        "Operações e tomada de decisão",
        "Cenários, capacidade e escolhas da fábrica",
        ft.Icons.PRECISION_MANUFACTURING_ROUNDED,
        s.PINK,
        ("Tomada de decisão", "Custo de oportunidade", "Análise de cenários", "Comprar ou alugar", "Capacidade produtiva"),
    ),
)


def level_by_key(key: str | None) -> Level | None:
    return next((level for level in LEVELS if level.key == key), None)


@dataclass(slots=True)
class _Topic:
    """Uma caixinha do quadro e o nível a que pertence."""

    text: str
    level: Level
    box: ft.Container
    label: ft.Text


class LevelsScreen:
    def __init__(
        self,
        page: ft.Page,
        *,
        on_select: Callable[[str], None],
        on_tracks: Callable[[], None] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.page = page
        self.on_select = on_select
        self.on_tracks = on_tracks  # volta à página das trilhas
        self.rng = rng or random.Random()
        self.layout = layout_for(page.width)
        self.generation = 0
        self.rendered_size: tuple[float, float] = (0, 0)
        self.topics: list[_Topic] = []
        self.highlight: Level | None = None
        self.caption = ft.Text()
        self.hovering = False  # com o mouse sobre um nível, o destaque automático pausa

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
        size = (self.page.width or 0, self.page.height or 0)
        self.layout = layout_for(getattr(event, "width", None) or self.page.width)
        if size != self.rendered_size:
            self.show()

    async def _float_loop(self, generation: int) -> None:
        """As caixinhas balançam devagar; no celular o destaque passa de nível em nível."""

        up, tick = True, 0
        while generation == self.generation:
            for index, topic in enumerate(self.topics):
                direction = -1 if (index % 2 == 0) == up else 1
                topic.box.offset = ft.Offset(0.04 * direction, (0.12 if self.compact else 0.22) * direction)
            if self.compact and not self.hovering and tick % AUTO_HIGHLIGHT_TICKS == 0:
                current = LEVELS.index(self.highlight) if self.highlight else -1
                self._set_highlight(LEVELS[(current + 1) % len(LEVELS)], update=False)
            up, tick = not up, tick + 1
            self.page.update()
            await asyncio.sleep(FLOAT_PERIOD_SECONDS)

    # ------------------------------------------------------------ desenho
    @property
    def compact(self) -> bool:
        return self.layout is Layout.COMPACT

    def build(self) -> ft.Control:
        width = self.page.width or 1280
        height = self.page.height or 720
        self.rendered_size = (self.page.width or 0, self.page.height or 0)
        short = height < 900
        align = ft.CrossAxisAlignment.CENTER if self.compact else ft.CrossAxisAlignment.START
        text_align = ft.TextAlign.CENTER if self.compact else ft.TextAlign.START

        header = ft.Column(
            [
                ft.Row(
                    [s.chip("ENGENHARIA DE PRODUÇÃO", icon=ft.Icons.PRECISION_MANUFACTURING_ROUNDED, color=s.GREEN, size=11)],
                    alignment=ft.MainAxisAlignment.CENTER if self.compact else ft.MainAxisAlignment.START,
                ),
                s.gradient_text("Escolha o seu nível", 30 if self.compact else (40 if short else 46), [s.YELLOW, s.ORANGE, s.PINK]),
                ft.Text(
                    "Toque em um nível para jogar." if self.compact else "Passe o mouse em um nível para ver os conteúdos e clique para jogar.",
                    size=14 if self.compact else 16,
                    color=s.MUTED,
                    text_align=text_align,
                ),
            ],
            spacing=8,
            horizontal_alignment=align,
        )
        buttons = ft.Column([self._level_button(level) for level in LEVELS], spacing=12 if short else 16)

        if self.compact:
            board = self._board(width=min(width - 36, 420), height=300)
            body: ft.Control = ft.Container(
                padding=ft.Padding.only(left=18, right=18, top=72, bottom=20),
                content=ft.Column(
                    [header, buttons, ft.Row([board], alignment=ft.MainAxisAlignment.CENTER)],
                    spacing=18,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            )
        else:
            left_width = 520 if width >= 1300 else 440
            board_width = max(300, min(width - left_width - 160, 640))
            board_height = max(320, min(height - 140, 560))
            body = ft.Container(
                padding=ft.Padding.only(left=32, right=32, top=72, bottom=24),
                content=ft.Row(
                    [
                        ft.Column([header, buttons], spacing=20 if short else 28, width=left_width),
                        self._board(width=board_width, height=board_height),
                    ],
                    spacing=48,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                gradient=s.background(),
                content=ft.Stack(
                    [
                        ft.Container(
                            left=0,
                            top=0,
                            right=0,
                            bottom=0,
                            content=ft.Column(
                                [body],
                                scroll=ft.ScrollMode.AUTO,
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ),
                        *self._back_button(),
                    ],
                    expand=True,
                ),
            ),
        )

    def _level_button(self, level: Level) -> ft.Container:
        return ft.Container(
            data=level.key,
            on_click=self._choose,
            on_hover=self._hover_level,
            ink=True,
            scale=1,
            animate_scale=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14 if self.compact else 18),
            border_radius=24,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=[ft.Colors.with_opacity(0.30, level.color), ft.Colors.with_opacity(0.10, s.WHITE)],
            ),
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.8, level.color)),
            shadow=ft.BoxShadow(blur_radius=24, color=ft.Colors.with_opacity(0.35, level.color), offset=ft.Offset(0, 6)),
            content=ft.Row(
                [
                    ft.Container(
                        width=54,
                        height=54,
                        border_radius=18,
                        bgcolor=level.color,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(str(level.number), size=28, weight=ft.FontWeight.W_900, color=s.BG_TOP),
                    ),
                    ft.Column(
                        [
                            ft.Text(f"NÍVEL {level.number}", size=11, weight=ft.FontWeight.BOLD, color=level.color),
                            ft.Text(level.title, size=16 if self.compact else 19, weight=ft.FontWeight.W_900, color=s.WHITE),
                            # No celular, sem o subtítulo, para o quadro aparecer logo abaixo.
                            *([] if self.compact else [ft.Text(level.subtitle, size=13, color=s.MUTED)]),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=s.WHITE, size=26),
                ],
                spacing=14,
            ),
        )

    def _board(self, *, width: float, height: float) -> ft.Container:
        """Quadro de vidro com os conteúdos dos três níveis flutuando, misturados."""

        font = 12 if self.compact else 15
        pad = 10 if self.compact else 14
        entries = [(topic, level) for level in LEVELS for topic in level.topics]
        random.Random(7).shuffle(entries)  # sempre a mesma mistura, para o quadro não "pular"
        head = 44 if self.compact else 30  # espaço da legenda no topo do quadro
        inner_width = width - 2 * pad - 12  # folga para o aumento do destaque não sair do quadro
        # Distribui as caixinhas em linhas, com larguras estimadas pelo texto.
        rows: list[list[tuple[str, Level, float]]] = [[]]
        used = 0.0
        for text, level in entries:
            box_width = len(text) * font * 0.62 + 28
            if rows[-1] and used + box_width + 12 > inner_width:
                rows.append([])
                used = 0.0
            rows[-1].append((text, level, box_width))
            used += box_width + 12
        jitter = random.Random(11)
        # Altura mínima por linha: a caixinha, o balanço e o aumento do destaque.
        row_height = max((height - 2 * pad - head) / len(rows), font * 3.8)
        height = max(height, 2 * pad + head + row_height * len(rows))
        self.topics = []
        controls: list[ft.Control] = []
        for row_index, row in enumerate(rows):
            total = sum(w for *_, w in row) + 12 * (len(row) - 1)
            free = max(0.0, inner_width - total)
            x = pad + free * jitter.uniform(0.1, 0.9) / 2
            gap = 12 + (free / 2) / max(1, len(row) - 1)
            for text, level, box_width in row:
                top = pad + head + row_index * row_height + jitter.uniform(0.05, 0.35) * (row_height - font * 2.8)
                label = ft.Text(text, size=font, weight=ft.FontWeight.W_800, color=s.WHITE, no_wrap=True)
                box = ft.Container(
                    left=x,
                    top=top,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6 if self.compact else 8),
                    border_radius=12,
                    content=label,
                    offset=ft.Offset(0, 0),
                    scale=1,
                    animate_offset=ft.Animation(int(FLOAT_PERIOD_SECONDS * 1000), ft.AnimationCurve.EASE_IN_OUT),
                    animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                    animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                    animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                )
                topic = _Topic(text, level, box, label)
                self._paint(topic)
                self.topics.append(topic)
                controls.append(box)
                x += box_width + gap
        self.caption = ft.Text(size=12 if self.compact else 13, weight=ft.FontWeight.BOLD, max_lines=2, expand=True)
        self._paint_caption()
        heading = ft.Container(
            left=pad + 4,
            top=pad - 2,
            right=pad,
            content=ft.Row(
                [ft.Icon(ft.Icons.AUTO_AWESOME, color=s.FRAME, size=16), self.caption],
                spacing=6,
            ),
        )
        return ft.Container(
            width=width,
            height=height,
            border_radius=28,
            bgcolor=ft.Colors.with_opacity(0.08, s.WHITE),
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.35, s.FRAME)),
            shadow=ft.BoxShadow(blur_radius=50, color=ft.Colors.with_opacity(0.25, s.FRAME)),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Stack([heading, *controls], width=width, height=height),
        )

    def _paint(self, topic: _Topic) -> None:
        """Cores da caixinha conforme o nível destacado."""

        box, level = topic.box, topic.level
        if self.highlight is None:
            box.bgcolor = ft.Colors.with_opacity(0.12, s.WHITE)
            box.border = ft.Border.all(1.2, ft.Colors.with_opacity(0.55, s.FRAME))
            box.shadow = None
            box.scale, box.opacity = 1, 0.95
            topic.label.color = s.WHITE
        elif self.highlight is level:
            box.bgcolor = level.color
            box.border = ft.Border.all(1.5, s.WHITE)
            box.shadow = ft.BoxShadow(blur_radius=22, color=ft.Colors.with_opacity(0.7, level.color))
            box.scale, box.opacity = HIGHLIGHT_SCALE, 1
            topic.label.color = s.BG_TOP
        else:
            box.bgcolor = ft.Colors.with_opacity(0.06, s.WHITE)
            box.border = ft.Border.all(1, ft.Colors.with_opacity(0.2, s.WHITE))
            box.shadow = None
            box.scale, box.opacity = 0.92, 0.3
            topic.label.color = s.MUTED

    def _paint_caption(self) -> None:
        level = self.highlight
        if level is None:
            self.caption.value = "CONTEÚDOS DA TRILHA"
            self.caption.color = s.FRAME
        else:
            self.caption.value = f"NÍVEL {level.number} • {level.title.upper()}"
            self.caption.color = level.color

    def _set_highlight(self, level: Level | None, *, update: bool = True) -> None:
        self.highlight = level
        for topic in self.topics:
            self._paint(topic)
        self._paint_caption()
        if update:
            self.page.update()

    def _back_button(self) -> list[ft.Control]:
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

    # ------------------------------------------------------------ ações
    def _hover_level(self, event: Any) -> None:
        hovered = event.data in (True, "true")
        self.hovering = hovered
        event.control.scale = HOVER_SCALE if hovered else 1
        self._set_highlight(level_by_key(event.control.data) if hovered else None)

    def _choose(self, event: Any) -> None:
        self.stop()
        self.on_select(event.control.data)

    def _back_to_tracks(self, _: Any = None) -> None:
        self.stop()
        if self.on_tracks is not None:
            self.on_tracks()
