"""Página simulada para testar as telas sem abrir janela."""

from types import SimpleNamespace
from typing import Any

import flet as ft


class FakePage:
    """Implementa só o que a interface usa de ``ft.Page``."""

    def __init__(self, width: float | None = 1280, height: float | None = 720) -> None:
        self.width, self.height = width, height
        self.controls: list[ft.Control] = []
        self.dialogs: list[ft.Control] = []
        self.tasks: list[Any] = []
        self.updates = 0
        self.on_resize: Any = None
        self.on_disconnect: Any = None
        self.services: list[Any] = []

    def add(self, control: ft.Control) -> None:
        self.controls.append(control)

    def update(self, *_: Any) -> None:
        self.updates += 1

    def show_dialog(self, dialog: ft.Control) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self) -> None:
        if self.dialogs:
            self.dialogs.pop()

    def run_task(self, handler: Any, *args: Any) -> None:
        self.tasks.append((handler, args))

    def resize(self, width: float, height: float) -> None:
        self.width, self.height = width, height
        self.on_resize(SimpleNamespace(width=width, height=height))


def walk(control: Any):
    """Percorre a árvore de controles."""

    yield control
    children = list(getattr(control, "controls", None) or [])
    for attr in ("content", "title"):
        child = getattr(control, attr, None)
        if isinstance(child, ft.Control):
            children.append(child)
    for child in children:
        yield from walk(child)


def press(dialog: ft.AlertDialog, label: str) -> None:
    button = next(b for b in dialog.actions if b.content == label)
    button.on_click(None)
