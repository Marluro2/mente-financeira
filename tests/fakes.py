"""Página simulada para testar as telas sem abrir janela."""

import asyncio
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import Any

import flet as ft

Handler = Callable[[dict[str, Any]], Awaitable[None]]


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

    async def launch_url(self, url: str) -> None:
        self.launched = url

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


def started_shell(*args: Any, **kwargs: Any):
    """Abre o jogo e entra na trilha do Ensino Fundamental 2 (abertura do jogo)."""

    from mente_financeira.ui.shell import GameShell
    from mente_financeira.ui.tracks import FUNDAMENTAL

    shell = GameShell(*args, **kwargs)
    shell.open_track(FUNDAMENTAL)
    return shell


class FakeHub:
    """Faz o papel do pubsub do Flet: guarda os recados e entrega com ``flush``."""

    def __init__(self) -> None:
        self.handlers: dict[str, list[tuple[str, Handler]]] = {}
        self.queue: list[tuple[str, dict[str, Any]]] = []

    def messenger(self, owner: str) -> FakeMessenger:
        return FakeMessenger(self, owner)

    def flush(self) -> None:
        while self.queue:
            topic, message = self.queue.pop(0)
            for _, handler in list(self.handlers.get(topic, [])):
                asyncio.run(handler(message))


class FakeMessenger:
    def __init__(self, hub: FakeHub, owner: str) -> None:
        self.hub, self.owner = hub, owner

    def subscribe(self, topic: str, handler: Handler) -> None:
        self.hub.handlers.setdefault(topic, []).append((self.owner, handler))

    def send(self, topic: str, message: dict[str, Any]) -> None:
        self.hub.queue.append((topic, message))

    def close(self) -> None:
        for topic, handlers in self.hub.handlers.items():
            self.hub.handlers[topic] = [(o, h) for o, h in handlers if o != self.owner]
