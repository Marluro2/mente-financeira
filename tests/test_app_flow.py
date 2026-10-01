"""Percorre o fluxo real das telas com uma página simulada (sem abrir janela)."""

import asyncio
from pathlib import Path
import random
from types import SimpleNamespace
from typing import Any

import flet as ft
import pytest

from mente_financeira.content import load_track
from mente_financeira.core import QUESTION, RESOLUTION, GameSession
from mente_financeira.storage import Settings, SettingsStore
from mente_financeira.ui import app as app_module
from mente_financeira.ui.app import MemoryFinanceApp
from mente_financeira.ui.layout import Layout

PHONE, TABLET, DESKTOP = (360, 740), (800, 1100), (1280, 720)


class FakePage:
    """Implementa só o que a interface usa de ``ft.Page``."""

    def __init__(self, width: float | None = DESKTOP[0], height: float | None = DESKTOP[1]) -> None:
        self.width, self.height = width, height
        self.controls: list[ft.Control] = []
        self.dialogs: list[ft.Control] = []
        self.tasks: list[Any] = []
        self.updates = 0

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


def _press(dialog: ft.AlertDialog, label: str) -> None:
    button = next(b for b in dialog.actions if b.content == label)
    button.on_click(None)


def _click(app: MemoryFinanceApp, side: str, pair_id: str) -> None:
    card = SimpleNamespace(data=(side, pair_id))
    asyncio.run(app._on_card_click(SimpleNamespace(control=card)))


def _dialog_text(dialog: ft.Control) -> str:
    content = dialog.content
    return content.value if isinstance(content, ft.Text) else content.controls[0].value


def _walk(control: Any):
    yield control
    children = list(getattr(control, "controls", None) or [])
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        children.append(content)
    for child in children:
        yield from _walk(child)


def _make_app(tmp_path: Path, size: tuple[int, int]) -> MemoryFinanceApp:
    session = GameSession(load_track("medio"), random.Random(3))
    return MemoryFinanceApp(FakePage(*size), session=session, store=SettingsStore(tmp_path))  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _no_reveal_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "REVEAL_DELAY_SECONDS", 0)


@pytest.fixture(params=[PHONE, TABLET, DESKTOP], ids=["celular", "tablet", "computador"])
def app(request: pytest.FixtureRequest, tmp_path: Path) -> MemoryFinanceApp:
    return _make_app(tmp_path, request.param)


# ------------------------------------------------------------------ fluxo
def test_full_phase_flow(app: MemoryFinanceApp) -> None:
    page: FakePage = app.page  # type: ignore[assignment]
    app.name_1.value, app.name_2.value = "Ana", "Bruno"
    app._prepare_players(None)
    _press(page.dialogs[-1], "Iniciar jogo")

    session = app.session
    assert session.players == ["Ana", "Bruno"] and session.phase_active
    assert len(page.tasks) == 1  # cronômetro iniciado
    assert len(app.left_cards.controls) == len(session.pairs)

    # erro: passa a vez
    first = session.question_order[0]
    wrong = next(pid for pid in session.resolution_order if pid != first)
    _click(app, QUESTION, first)
    _click(app, RESOLUTION, wrong)
    assert session.turn == 1 and "Ainda não" in _dialog_text(page.dialogs[-1])

    # resolução antes da questão: aviso
    _click(app, RESOLUTION, first)
    assert "Comece escolhendo" in _dialog_text(page.dialogs[-1])

    # acertos até o fim da fase
    for pid in list(session.question_order):
        _click(app, QUESTION, pid)
        _click(app, RESOLUTION, pid)
        assert page.dialogs[-1].title.value == "Par encontrado! 🎉"
        _press(page.dialogs[-1], "Continuar")
    assert page.dialogs[-1].title.value == "Fase concluída! 🏆"
    assert session.scores == [0, 4]
    assert app.advance_button.visible

    app._advance_phase()
    assert session.phase_index == 1 and session.phase_active
    assert len(page.tasks) == 2


def test_timeout_offers_repeat(app: MemoryFinanceApp) -> None:
    page: FakePage = app.page  # type: ignore[assignment]
    app._begin_game()
    app.session.time_left = 1
    assert app.session.tick()
    app._handle_timeout()
    _press(page.dialogs[-1], "Repetir fase")
    assert app.session.phase_active and app.session.time_left == app.session.timer_seconds


def test_theme_choice_is_saved(app: MemoryFinanceApp, tmp_path: Path) -> None:
    app._begin_game()
    app._change_palette(SimpleNamespace(control=SimpleNamespace(value="neon")))
    app._toggle_dark_mode(SimpleNamespace(control=SimpleNamespace(value=True)))
    assert SettingsStore(tmp_path).load() == Settings(palette="neon", dark_mode=True)


def test_final_phase_shows_results_and_restarts(app: MemoryFinanceApp) -> None:
    page: FakePage = app.page  # type: ignore[assignment]
    app._begin_game()
    session = app.session
    session.phase_index = session.phase_count - 1
    app._start_phase(repeat=False)
    for pid in list(session.question_order):
        _click(app, QUESTION, pid)
        _click(app, RESOLUTION, pid)
        _press(page.dialogs[-1], "Continuar")
    _press(page.dialogs[-1], "Ver tabuleiro")
    app._advance_phase()
    assert page.dialogs[-1].title.value == "Jornada concluída! 🎓"
    _press(page.dialogs[-1], "Jogar novamente")
    assert not session.phase_active
    assert app.screen == "start"


def test_found_pair_can_be_reviewed(app: MemoryFinanceApp) -> None:
    page: FakePage = app.page  # type: ignore[assignment]
    app._begin_game()
    pid = app.session.question_order[0]
    _click(app, QUESTION, pid)
    _click(app, RESOLUTION, pid)
    _press(page.dialogs[-1], "Continuar")
    _click(app, RESOLUTION, pid)
    review = page.dialogs[-1]
    assert review.title.value == "Par encontrado ✓"
    assert app.session.pairs_by_id[pid].question in _dialog_text(review)
    assert not app.session.timer_paused


# ------------------------------------------------------------------ layout
def test_screens_have_no_expanded_child_inside_wrapping_row(app: MemoryFinanceApp) -> None:
    # No Flutter, isso gera erro de layout (bloco cinza na tela).
    def offenders(root: ft.Control) -> list[ft.Control]:
        return [
            child
            for control in _walk(root)
            if isinstance(control, ft.Row) and control.wrap
            for child in control.controls
            if child.expand
        ]

    page: FakePage = app.page  # type: ignore[assignment]
    assert offenders(page.controls[-1]) == []  # tela inicial
    app._begin_game()
    assert offenders(page.controls[-1]) == []  # tabuleiro
    assert offenders(app.whiteboard.panel) == []


def test_start_card_fits_the_screen(app: MemoryFinanceApp) -> None:
    page: FakePage = app.page  # type: ignore[assignment]
    widths = [c.width for c in _walk(page.controls[-1]) if isinstance(c, ft.Container) and c.width]
    assert max(widths) <= page.width


@pytest.mark.parametrize(
    ("width", "expected"),
    [(None, Layout.WIDE), (360, Layout.COMPACT), (699, Layout.COMPACT), (700, Layout.MEDIUM), (1099, Layout.MEDIUM), (1100, Layout.WIDE)],
)
def test_layout_bands(tmp_path: Path, width: int | None, expected: Layout) -> None:
    assert _make_app(tmp_path, (width, 700)).layout is expected


def test_phone_opens_whiteboard_in_bottom_sheet(tmp_path: Path) -> None:
    app = _make_app(tmp_path, PHONE)
    page: FakePage = app.page  # type: ignore[assignment]
    app._begin_game()
    assert app.whiteboard.panel not in app.game_body.controls
    app._toggle_whiteboard()
    assert isinstance(page.dialogs[-1], ft.BottomSheet)
    assert app.whiteboard_button.tooltip == "Fechar lousa"
    app._toggle_whiteboard()
    assert not any(isinstance(d, ft.BottomSheet) for d in page.dialogs)
    assert app.whiteboard_button.tooltip == "Abrir lousa"


def test_phone_whiteboard_shows_the_open_question(tmp_path: Path) -> None:
    app = _make_app(tmp_path, PHONE)
    app._begin_game()
    app._toggle_whiteboard()
    assert not app.whiteboard.prompt_box.visible  # nenhuma questão aberta
    app._toggle_whiteboard()
    pid = app.session.question_order[0]
    _click(app, QUESTION, pid)
    app._toggle_whiteboard()
    assert app.whiteboard.prompt_box.visible
    assert app.whiteboard.prompt_text.value == app.session.pairs_by_id[pid].question


def test_restart_asks_for_confirmation(app: MemoryFinanceApp) -> None:
    page: FakePage = app.page  # type: ignore[assignment]
    app._begin_game()
    app._confirm_restart()
    _press(page.dialogs[-1], "Continuar jogando")
    assert app.screen == "game" and app.session.phase_active
    app._confirm_restart()
    _press(page.dialogs[-1], "Reiniciar")
    assert app.screen == "start"


def test_desktop_keeps_whiteboard_beside_the_board(tmp_path: Path) -> None:
    app = _make_app(tmp_path, DESKTOP)
    app._begin_game()
    assert app.whiteboard.panel in app.game_body.controls
    app._toggle_whiteboard()
    assert app.whiteboard.panel.visible


def test_phone_shows_open_question_in_full(tmp_path: Path) -> None:
    app = _make_app(tmp_path, PHONE)
    app._begin_game()
    assert not app.focus_box.visible
    pid = app.session.question_order[0]
    _click(app, QUESTION, pid)
    assert app.focus_box.visible
    assert app.focus_text.value == app.session.pairs_by_id[pid].question


@pytest.mark.parametrize("size", [TABLET, DESKTOP], ids=["tablet", "computador"])
def test_larger_screens_do_not_need_the_question_strip(tmp_path: Path, size: tuple[int, int]) -> None:
    app = _make_app(tmp_path, size)
    app._begin_game()
    _click(app, QUESTION, app.session.question_order[0])
    assert not app.focus_box.visible


def test_rotating_during_a_phase_keeps_the_game(tmp_path: Path) -> None:
    app = _make_app(tmp_path, DESKTOP)
    page: FakePage = app.page  # type: ignore[assignment]
    app._begin_game()
    pid = app.session.question_order[0]
    _click(app, QUESTION, pid)
    _click(app, RESOLUTION, pid)
    _press(page.dialogs[-1], "Continuar")
    app.whiteboard.line_specs.append((0, 0, 10, 10, "#000000", 3.0))
    app.whiteboard.stroke_starts.append(0)

    page.resize(*PHONE)
    assert app.layout is Layout.COMPACT
    assert app.session.scores == [1, 0] and pid in app.session.matched
    assert len(page.tasks) == 1  # o cronômetro não foi reiniciado
    assert len(app.whiteboard.line_specs) == 1  # o rascunho foi mantido
    assert app.whiteboard_sheet is not None


def test_resizing_start_screen_keeps_typed_names(tmp_path: Path) -> None:
    app = _make_app(tmp_path, DESKTOP)
    page: FakePage = app.page  # type: ignore[assignment]
    app.name_1.value = "Ana"
    page.resize(*PHONE)
    assert app.screen == "start" and app.name_1.value == "Ana"


def test_phone_appearance_menu_changes_theme(tmp_path: Path) -> None:
    app = _make_app(tmp_path, PHONE)
    app._begin_game()
    menu = next(c for c in _walk(app.page.controls[-1]) if isinstance(c, ft.PopupMenuButton))
    neon = next(item for item in menu.items if item.data == "neon")
    neon.on_click(SimpleNamespace(control=neon))
    assert app.palette_key == "neon"
    menu = next(c for c in _walk(app.page.controls[-1]) if isinstance(c, ft.PopupMenuButton))
    dark = next(item for item in menu.items if item.content == "Modo escuro")
    dark.on_click(SimpleNamespace(control=dark))
    assert app.dark_mode
