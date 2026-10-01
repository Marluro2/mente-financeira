import inspect
import random

import flet as ft

from mente_financeira.content import load_track
from mente_financeira.core import QUESTION, RESOLUTION, GameSession
from mente_financeira.ui import MemoryFinanceApp
from mente_financeira.ui.layout import Layout


def _card_app() -> MemoryFinanceApp:
    app = MemoryFinanceApp.__new__(MemoryFinanceApp)
    app.palette_key = "kids"
    app.dark_mode = False
    app.layout = Layout.WIDE
    app.session = GameSession(load_track("medio"), random.Random(0))
    app.session.new_game()
    return app


def test_game_screen_does_not_enable_vertical_scrolling() -> None:
    source = inspect.getsource(MemoryFinanceApp._render_game_screen)
    assert "scroll=ft.ScrollMode.AUTO" not in source
    assert "self.game_body" in source


def test_memory_cards_share_the_available_height() -> None:
    app = _card_app()
    pid = app.session.question_order[0]
    question = app._memory_card(QUESTION, pid, 1)
    resolution = app._memory_card(RESOLUTION, pid, 1)

    assert question.expand is True
    assert resolution.expand is True
    assert question.height is None
    assert resolution.height is None


def test_board_has_one_card_per_pair_on_each_side() -> None:
    app = _card_app()
    assert len(app._build_cards(QUESTION)) == len(app.session.pairs)
    assert len(app._build_cards(RESOLUTION)) == len(app.session.pairs)


def test_question_and_resolution_panels_are_both_flexible() -> None:
    app = _card_app()
    questions = app._side_panel(QUESTION, ft.Column(expand=True))
    resolutions = app._side_panel(RESOLUTION, ft.Column(expand=True))

    assert questions.expand is True
    assert resolutions.expand is True
