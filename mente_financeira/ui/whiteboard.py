"""Lousa de cálculo desenhada com a API de gestos e de canvas do Flet."""

from __future__ import annotations

from collections.abc import Callable
import math
from typing import Any

import flet as ft
import flet.canvas as cv

from mente_financeira.ui.theme import Palette

LineSpec = tuple[float, float, float, float, str, float]

# Cada segmento desenhado é enviado do Python para a tela. Amostrar o gesto a
# cada 20 ms e ignorar deslocamentos menores que 2 px reduz bastante o tráfego
# no celular sem prejudicar o traço.
DRAG_INTERVAL_MS = 20
MIN_SEGMENT_PX = 2.0


class Whiteboard:
    """Lousa vetorial baseada na API de gestos do Flet 0.86."""

    def __init__(
        self,
        palette: Palette,
        dark_mode: bool,
        *,
        canvas_height: float = 230,
        on_close: Callable[[], None] | None = None,
        show_title: bool = True,  # False: sem o título "Lousa de cálculo" (economiza altura)
    ) -> None:
        self.palette = palette
        self.dark_mode = dark_mode
        self.color = "#17202A"
        self.stroke_width = 3.0
        self.last_point: tuple[float, float] | None = None
        self.stroke_starts: list[int] = []
        self.line_specs: list[LineSpec] = []
        self.color_controls: dict[str, ft.Container] = {}

        self.canvas = cv.Canvas(shapes=[], expand=True)
        self.tools = ft.Row(spacing=8, wrap=True, alignment=ft.MainAxisAlignment.CENTER)
        self._rebuild_tools()

        # A API atual expõe local_position.x/y. local_x/local_y não existem em
        # DragStartEvent e DragUpdateEvent no Flet 0.86.
        detector = ft.GestureDetector(
            content=ft.Container(
                content=self.canvas,
                height=canvas_height,
                bgcolor="#FFFFFF",
                border_radius=16,
                border=ft.Border.all(1, "#D7DCE3"),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
            drag_interval=DRAG_INTERVAL_MS,
            on_pan_start=self._start_stroke,
            on_pan_update=self._draw_stroke,
            on_pan_end=self._end_stroke,
            on_pan_cancel=self._cancel_stroke,
        )

        # Enunciado em que o aluno está trabalhando, visível sobre a lousa
        # quando ela cobre o tabuleiro (painel deslizante do celular).
        self.prompt_text = ft.Text(size=13, weight=ft.FontWeight.W_500, color=self._text)
        self.prompt_box = ft.Container(
            visible=False,
            padding=10,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.10, palette.primary),
            border=ft.Border.all(1, palette.primary),
            content=self.prompt_text,
        )

        self.panel = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        visible=show_title,
                        controls=[
                            ft.Icon(ft.Icons.DRAW, color=palette.primary),
                            ft.Column(
                                [
                                    ft.Text("Lousa de cálculo", size=18, weight=ft.FontWeight.BOLD, color=self._text),
                                    ft.Text("Rascunhe contas com o mouse, a caneta ou o toque.", size=12, color=self._muted),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            *(
                                [ft.IconButton(ft.Icons.CLOSE, tooltip="Fechar lousa", icon_color=self._text, on_click=lambda _: on_close())]
                                if on_close
                                else []
                            ),
                        ],
                    ),
                    self.prompt_box,
                    self.tools,
                    detector,
                ],
                spacing=12,
                # tight: a lousa ocupa só a altura do conteúdo (no painel
                # deslizante do celular, não cobre a tela inteira).
                tight=True,
            ),
            padding=16,
            bgcolor=self._surface,
            border_radius=22,
            border=ft.Border.all(1, self._border),
        )

    # Cores explícitas: a lousa não depende do tema da página (a abertura e o
    # Nível 1 usam tema escuro, mas a lousa do desafio é clara).
    @property
    def _text(self) -> str:
        return "#F7F3FA" if self.dark_mode else "#211D25"

    @property
    def _surface(self) -> str:
        return self.palette.dark_surface if self.dark_mode else self.palette.light_surface

    @property
    def _border(self) -> str:
        return "#473E5E" if self.dark_mode else "#E4E0EA"

    @property
    def _muted(self) -> str:
        return "#C9C3D6" if self.dark_mode else "#625C6B"

    def set_prompt(self, text: str | None) -> None:
        self.prompt_text.value = text or ""
        self.prompt_box.visible = bool(text)

    def _rebuild_tools(self) -> None:
        colors = ("#17202A", "#D62828", "#0066CC", "#12805C", "#7B2CBF")
        self.color_controls.clear()
        controls: list[ft.Control] = []
        for color in colors:
            item = ft.Container(
                width=32,
                height=32,
                bgcolor=color,
                border_radius=16,
                border=ft.Border.all(3 if self.color == color else 1, self.palette.secondary if self.color == color else "#B7BCC5"),
                data=color,
                tooltip=f"Lápis {color}",
                on_click=self._select_color,
            )
            self.color_controls[color] = item
            controls.append(item)
        controls.extend(
            [
                ft.IconButton(ft.Icons.EDIT_OFF, tooltip="Borracha", icon_color=self._text, on_click=self._select_eraser),
                ft.IconButton(ft.Icons.UNDO, tooltip="Desfazer último traço", icon_color=self._text, on_click=self._undo),
                ft.IconButton(ft.Icons.DELETE_SWEEP, tooltip="Limpar lousa", icon_color=self._text, on_click=self._clear_click),
            ]
        )
        self.tools.controls = controls

    def update_theme(self, palette: Palette, dark_mode: bool) -> None:
        self.palette = palette
        self.dark_mode = dark_mode
        self.panel.bgcolor = self._surface
        self.panel.border = ft.Border.all(1, self._border)
        self._rebuild_tools()

    def _select_color(self, event: Any) -> None:
        self.color = str(event.control.data)
        self.stroke_width = 3.0
        self._rebuild_tools()
        self.tools.update()

    def _select_eraser(self, _: Any) -> None:
        self.color = "#FFFFFF"
        self.stroke_width = 18.0
        self._rebuild_tools()
        self.tools.update()

    def _start_stroke(self, event: ft.DragStartEvent) -> None:
        point = event.local_position
        self.last_point = (float(point.x), float(point.y))
        self.stroke_starts.append(len(self.canvas.shapes))

    def _draw_stroke(self, event: ft.DragUpdateEvent) -> None:
        if self.last_point is None:
            return
        point = event.local_position
        current = (float(point.x), float(point.y))
        if math.dist(self.last_point, current) < MIN_SEGMENT_PX:
            return
        spec = (self.last_point[0], self.last_point[1], current[0], current[1], self.color, self.stroke_width)
        self.line_specs.append(spec)
        self.canvas.shapes.append(self._make_line(spec))
        self.last_point = current
        self.canvas.update()

    def _end_stroke(self, _: ft.DragEndEvent) -> None:
        self.last_point = None

    def _cancel_stroke(self, _: Any = None) -> None:
        self.last_point = None

    def _undo(self, _: Any) -> None:
        if not self.stroke_starts:
            return
        start = self.stroke_starts.pop()
        del self.canvas.shapes[start:]
        del self.line_specs[start:]
        self.canvas.update()

    def _clear_click(self, _: Any) -> None:
        self.clear()

    def clear(self, update: bool = True) -> None:
        self.canvas.shapes.clear()
        self.line_specs.clear()
        self.stroke_starts.clear()
        self.last_point = None
        if update:
            self.canvas.update()

    @staticmethod
    def _make_line(spec: LineSpec) -> cv.Line:
        x1, y1, x2, y2, color, width = spec
        return cv.Line(x1, y1, x2, y2, paint=ft.Paint(color=color, stroke_width=width, stroke_cap=ft.StrokeCap.ROUND))

    def snapshot(self) -> tuple[list[LineSpec], list[int]]:
        return self.line_specs.copy(), self.stroke_starts.copy()

    def restore(self, snapshot: tuple[list[LineSpec], list[int]]) -> None:
        lines, starts = snapshot
        self.line_specs = lines.copy()
        self.stroke_starts = starts.copy()
        self.canvas.shapes = [self._make_line(spec) for spec in self.line_specs]
