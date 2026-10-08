"""Formulário "Deixe sua sugestão" dentro do jogo (usado na feira, sem internet)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import flet as ft

from mente_financeira.sugestoes import LEVELS, TEXT_MAX, Suggestion, SuggestionError, make_suggestion
from mente_financeira.ui import style as s


def suggestion_button(on_click: Callable[[Any], None]) -> ft.Control:
    return ft.OutlinedButton(
        "Deixe sua sugestão",
        icon=ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=s.YELLOW,
            side=ft.BorderSide(2, s.YELLOW),
            shape=ft.RoundedRectangleBorder(radius=22),
            padding=ft.Padding.symmetric(horizontal=18, vertical=14),
            text_style=ft.TextStyle(size=15, weight=ft.FontWeight.W_900),
        ),
    )


class SuggestionForm:
    """Janela com a sugestão (obrigatória), o nível e a idade (opcionais)."""

    def __init__(self, page: ft.Page, on_save: Callable[[Suggestion], None]) -> None:
        self.page = page
        self.on_save = on_save
        field_style: dict[str, Any] = {
            "border_radius": 14,
            "filled": True,
            "bgcolor": ft.Colors.with_opacity(0.10, s.WHITE),
            "border_color": s.GLASS_BORDER,
            "focused_border_color": s.CYAN,
            "color": s.WHITE,
            "label_style": ft.TextStyle(color=s.MUTED),
        }
        self.text = ft.TextField(
            label="Sua sugestão",
            hint_text="O que podemos melhorar no jogo?",
            multiline=True,
            min_lines=3,
            max_lines=6,
            max_length=TEXT_MAX,
            **field_style,
        )
        self.level = ft.Dropdown(
            label="Nível (opcional)",
            options=[ft.DropdownOption(key=level, text=level) for level in LEVELS],
            expand=True,
            fill_color=ft.Colors.with_opacity(0.10, s.WHITE),
            **{k: v for k, v in field_style.items() if k != "bgcolor"},
        )
        self.age = ft.TextField(
            label="Idade (opcional)",
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=2,
            **field_style,
        )
        self.dialog = ft.AlertDialog(
            modal=True,
            bgcolor="#2A1A5E",
            title=ft.Text("Deixe sua sugestão 💡", weight=ft.FontWeight.W_900, color=s.WHITE),
            content=ft.Column(
                [
                    self.text,
                    self.level,
                    self.age,
                    ft.Text("Não escreva seu nome nem contato. A sugestão é anônima.", size=12, color=s.MUTED),
                ],
                spacing=12,
                tight=True,
                width=420,
            ),
            scrollable=True,
            actions=[
                ft.TextButton("Cancelar", on_click=self._cancel, style=ft.ButtonStyle(color=s.CYAN)),
                ft.Button(
                    "Enviar",
                    icon=ft.Icons.SEND_ROUNDED,
                    on_click=self._send,
                    style=ft.ButtonStyle(bgcolor=s.PINK, color=s.WHITE, shape=ft.RoundedRectangleBorder(radius=14)),
                ),
            ],
        )

    def open(self) -> None:
        self.page.show_dialog(self.dialog)

    def _cancel(self, _: Any = None) -> None:
        self.page.pop_dialog()

    def _send(self, _: Any = None) -> None:
        self.text.error = self.age.error = None
        try:
            suggestion = make_suggestion(self.text.value, self.level.value, self.age.value)
        except SuggestionError as error:
            target = self.age if "idade" in str(error).lower() else self.text
            target.error = str(error)
            self.page.update()
            return
        self.on_save(suggestion)
        self.page.pop_dialog()
        self.page.show_dialog(
            ft.SnackBar(
                ft.Text("Obrigado pela sugestão! 💡", color=s.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor="#E63A1C9C",
                behavior=ft.SnackBarBehavior.FLOATING,
                duration=2500,
            )
        )
