"""Fluxo da abertura e do Nível 1 com uma página simulada."""

import asyncio
from pathlib import Path
import random
from types import SimpleNamespace

import flet as ft
import pytest

from fakes import FakePage, press, started_shell, walk
from mente_financeira.core.memory_game import Mode
from mente_financeira.core.percent_challenge import ENCOURAGEMENTS
from mente_financeira.storage import SettingsStore
from mente_financeira.ui import memory_screen as memory_module
from mente_financeira.ui.app import MemoryFinanceApp
from mente_financeira.ui.home import HomeScreen
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.shell import GameShell

PHONE, DESKTOP = (360, 740), (1280, 720)


@pytest.fixture(autouse=True)
def _no_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory_module, "MISMATCH_DELAY_SECONDS", 0)
    monkeypatch.setattr(memory_module, "RESULT_DELAY_SECONDS", 0)


@pytest.fixture(params=[PHONE, DESKTOP], ids=["celular", "computador"])
def shell(request: pytest.FixtureRequest, tmp_path: Path) -> GameShell:
    return started_shell(FakePage(*request.param), store=SettingsStore(tmp_path), rng=random.Random(4))  # type: ignore[arg-type]


def _tap(screen: MemoryScreen, index: int) -> None:
    asyncio.run(screen._on_card_click(SimpleNamespace(control=SimpleNamespace(data=index))))


def _pair_of(screen: MemoryScreen, index: int) -> int:
    cards = screen.game.cards
    return next(i for i, c in enumerate(cards) if i != index and c.id == cards[index].id)


def _home(shell: GameShell) -> HomeScreen:
    assert isinstance(shell.current, HomeScreen)
    return shell.current


def _memory(shell: GameShell) -> MemoryScreen:
    assert isinstance(shell.current, MemoryScreen)
    return shell.current


# ------------------------------------------------------------------ abertura
def test_opens_on_the_home_screen(shell: GameShell) -> None:
    home = _home(shell)
    texts = [c.value for c in walk(shell.page.controls[-1]) if isinstance(c, ft.Text)]
    assert "MENTE" in texts and "FINANCEIRA" in texts
    assert "Desafio dos Cálculos" not in texts  # o Nível 2 não aparece mais na abertura
    assert home.mode is Mode.SOLO
    assert shell.page.tasks[-1][0] == home._float_loop  # animação dos ícones flutuantes


def test_duel_mode_asks_for_two_names(shell: GameShell) -> None:
    home = _home(shell)
    home._select_mode(SimpleNamespace(control=SimpleNamespace(data=Mode.DUEL)))
    home.name_1.value, home.name_2.value = "Ana", "Bruno"
    home._play()
    screen = _memory(shell)
    assert screen.game.mode is Mode.DUEL
    assert screen.game.players == ["Ana", "Bruno"]


def test_home_compacts_on_short_desktop_screens(tmp_path: Path) -> None:
    shell = started_shell(FakePage(1536, 1000), store=SettingsStore(tmp_path), rng=random.Random(4))  # type: ignore[arg-type]
    home = _home(shell)
    assert not home.short
    shell.page.resize(1536, 785)  # type: ignore[attr-defined]
    assert home.short and home.rendered_short  # redesenhou compacta
    title = next(c for c in walk(shell.page.controls[-1]) if isinstance(c, ft.Text) and c.value == "MENTE")
    assert title.size == 62


def test_home_float_animation_stops_when_leaving(shell: GameShell) -> None:
    home = _home(shell)
    generation = home.generation
    home._play()
    assert home.generation != generation


# ------------------------------------------------------------------ Nível 1
def test_solo_game_to_the_end(shell: GameShell) -> None:
    _home(shell)._play()
    screen = _memory(shell)
    page: FakePage = shell.page  # type: ignore[assignment]
    assert len(screen.cards) == 16

    # erro: cartas voltam a ficar viradas
    wrong = next(i for i, c in enumerate(screen.game.cards) if c.id != screen.game.cards[0].id)
    _tap(screen, 0)
    _tap(screen, wrong)
    assert not screen.game.is_revealed(0) and screen.game.moves == 1

    # acertos
    for index in range(16):
        if not screen.game.is_revealed(index):
            _tap(screen, index)
            _tap(screen, _pair_of(screen, index))
            assert screen.last_concept is screen.game.cards[index]
    assert screen.game.is_complete
    result = page.dialogs[-1]
    assert result.title.value == "Mandou bem! 🎉"
    texts = [c.value for c in walk(result) if isinstance(c, ft.Text)]
    assert "⭐⭐⭐" in texts  # 9 jogadas

    press(result, "Jogar de novo")
    assert shell.current is screen and screen.game.active and screen.game.moves == 0


def test_concept_panel_highlights_the_found_concept_with_example(shell: GameShell) -> None:
    _home(shell)._play()
    screen = _memory(shell)
    assert screen.panel_count.value == "0/8"
    assert not screen.learned_title.visible
    assert "Faltam 8 conceitos" in screen.locked_note.value
    _tap(screen, 0)
    _tap(screen, _pair_of(screen, 0))
    concept = screen.game.cards[0]
    texts = [c.value for c in walk(screen.tip_switcher) if isinstance(c, ft.Text)]
    assert concept.tip in texts and concept.name in texts and concept.example in texts
    assert "✨ NOVO CONCEITO!" in texts
    assert screen.panel_count.value == "1/8" and screen.panel_progress.value == 1 / 8
    assert len([c for c in walk(screen.learned_row) if isinstance(c, ft.Image)]) == 1
    assert "Faltam 7 conceitos" in screen.locked_note.value


def test_tapping_a_discovered_concept_brings_it_back(shell: GameShell) -> None:
    _home(shell)._play()
    screen = _memory(shell)
    for _ in range(2):
        index = next(i for i in range(16) if not screen.game.is_revealed(i))
        _tap(screen, index)
        _tap(screen, _pair_of(screen, index))
    first, second = screen.game.learned
    assert screen.last_concept is second
    items = screen.learned_row.controls
    assert [item.data for item in items] == [second, first]  # mais recente primeiro
    items[1].on_click(SimpleNamespace(control=items[1]))
    assert screen.last_concept is first
    texts = [c.value for c in walk(screen.tip_switcher) if isinstance(c, ft.Text)]
    assert first.example in texts and "CONCEITO" in texts


def test_desktop_panel_fills_the_right_side(tmp_path: Path) -> None:
    shell = started_shell(FakePage(*DESKTOP), store=SettingsStore(tmp_path), rng=random.Random(4))  # type: ignore[arg-type]
    _home(shell)._play()
    screen = _memory(shell)
    panel = next(
        c for c in walk(shell.page.controls[-1]) if isinstance(c, ft.Container) and c.content is not None
        and isinstance(c.content, ft.Column) and screen.tip_switcher in c.content.controls
    )
    assert panel.expand is True
    assert panel.height == pytest.approx(4 * screen.card_size + 3 * 12)


def test_leaving_mid_game_asks_confirmation(shell: GameShell) -> None:
    _home(shell)._play()
    screen = _memory(shell)
    page: FakePage = shell.page  # type: ignore[assignment]
    wrong = next(i for i, c in enumerate(screen.game.cards) if c.id != screen.game.cards[0].id)
    _tap(screen, 0)
    _tap(screen, wrong)
    screen._confirm_home()
    press(page.dialogs[-1], "Continuar jogando")
    assert shell.current is screen
    screen._confirm_home()
    press(page.dialogs[-1], "Voltar")
    assert isinstance(shell.current, HomeScreen)
    assert not screen.game.active


def test_resize_keeps_the_board(shell: GameShell) -> None:
    _home(shell)._play()
    screen = _memory(shell)
    _tap(screen, 0)
    _tap(screen, _pair_of(screen, 0))
    shell.page.resize(800, 600)  # type: ignore[attr-defined]
    assert screen.game.found_pairs == 1
    assert len(screen.cards) == 16


def test_cards_fit_on_screen(shell: GameShell) -> None:
    _home(shell)._play()
    screen = _memory(shell)
    page = shell.page
    grid_width = 4 * screen.card_size + 3 * (8 if screen.compact else 12)
    assert grid_width <= page.width
    assert screen.card_size >= 56


def test_no_expanded_child_inside_wrapping_row(shell: GameShell) -> None:
    def offenders(root: ft.Control) -> list[ft.Control]:
        return [
            child
            for control in walk(root)
            if isinstance(control, ft.Row) and control.wrap
            for child in control.controls
            if child.expand
        ]

    assert offenders(shell.page.controls[-1]) == []
    _home(shell)._play()
    assert offenders(shell.page.controls[-1]) == []


# ------------------------------------------------------- Desafio Relâmpago
def _duel(shell: GameShell) -> MemoryScreen:
    home = _home(shell)
    home._select_mode(SimpleNamespace(control=SimpleNamespace(data=Mode.DUEL)))
    home.name_1.value, home.name_2.value = "Ana", "Bruno"
    home._play()
    return _memory(shell)


def _find_pair(screen: MemoryScreen) -> None:
    index = next(i for i in range(16) if not screen.game.is_revealed(i))
    _tap(screen, index)
    _tap(screen, _pair_of(screen, index))


def _choose(screen: MemoryScreen, correct: bool) -> None:
    challenge = screen.challenge
    index = challenge.answer_index if correct else (challenge.answer_index + 1) % 4
    screen._answer_challenge(SimpleNamespace(control=SimpleNamespace(data=index)))


def _texts(control: ft.Control) -> list[str]:
    return [c.value for c in walk(control) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def test_duel_pair_opens_challenge_and_right_answer_keeps_turn(shell: GameShell) -> None:
    screen = _duel(shell)
    _find_pair(screen)
    assert screen.overlay.visible and screen.challenge is not None
    assert screen.challenge.question in _texts(screen.overlay)
    assert any("Vez de Ana" in t for t in _texts(screen.overlay))

    _tap(screen, next(i for i in range(16) if not screen.game.is_revealed(i)))
    assert not screen.game.face_up  # tabuleiro travado durante o desafio

    _choose(screen, correct=True)
    assert screen.feedback_box.visible
    assert screen.challenge_feedback in ENCOURAGEMENTS
    assert screen.continue_button.content.controls[1].value == "CONTINUAR JOGANDO"
    screen._close_challenge()
    assert not screen.overlay.visible
    assert screen.game.current_player == "Ana"


def test_wrong_answer_shows_solution_and_passes_turn(shell: GameShell) -> None:
    screen = _duel(shell)
    page: FakePage = shell.page  # type: ignore[assignment]
    _find_pair(screen)
    answer = screen.challenge.answer
    _choose(screen, correct=False)
    assert answer in screen.challenge_feedback
    assert screen.continue_button.content.controls[1].value == "PASSAR A VEZ PARA BRUNO"
    screen._close_challenge()
    assert screen.game.current_player == "Bruno"
    assert "Bruno" in page.dialogs[-1].content.value
    assert screen.game.scores == [1, 0]


def test_challenge_covers_the_whole_screen(shell: GameShell) -> None:
    screen = _duel(shell)
    _find_pair(screen)
    overlay = screen.overlay
    assert (overlay.left, overlay.top, overlay.right, overlay.bottom) == (0, 0, 0, 0)
    assert overlay.content.gradient is not None  # fundo próprio, sem mostrar o tabuleiro


def test_challenge_shows_situation_image_label_and_item(shell: GameShell) -> None:
    screen = _duel(shell)
    _find_pair(screen)
    challenge = screen.challenge
    texts = _texts(screen.overlay)
    assert challenge.label in texts and challenge.item in texts
    images = [c.src for c in walk(screen.overlay) if isinstance(c, ft.Image)]
    assert challenge.image in images
    assert screen.image_panel.visible
    screen._toggle_challenge_board()
    assert not screen.image_panel.visible  # a lousa ocupa o lugar da imagem
    screen._toggle_challenge_board()
    _choose(screen, correct=True)
    assert not screen.image_panel.visible and screen.feedback_box.visible  # comemoração no lugar
    letters = [c.value for c in walk(screen.overlay) if isinstance(c, ft.Text) and c.value in ("A.", "B.", "C.", "D.")]
    assert letters == ["A.", "B.", "C.", "D."]


def test_right_answer_gets_a_highlighted_celebration(shell: GameShell) -> None:
    screen = _duel(shell)
    _find_pair(screen)
    _choose(screen, correct=True)
    celebration = screen.feedback_switcher.content
    texts = _texts(celebration)
    assert "🎉" in texts and screen.challenge_feedback in texts
    assert "Ana, a vez continua sua!" in texts
    big = next(c for c in walk(celebration) if isinstance(c, ft.Text) and c.value == screen.challenge_feedback)
    assert big.size >= 26 and big.weight == ft.FontWeight.W_900
    assert celebration.gradient is not None


def test_wrong_answer_block_shows_whose_turn_is_next(shell: GameShell) -> None:
    screen = _duel(shell)
    _find_pair(screen)
    _choose(screen, correct=False)
    texts = _texts(screen.feedback_switcher.content)
    assert "💡" in texts and "A vez passa para Bruno." in texts
    assert any(screen.challenge.answer in t for t in texts)


def test_whiteboard_opens_inside_the_challenge(shell: GameShell) -> None:
    screen = _duel(shell)
    _find_pair(screen)
    board = screen.challenge_board
    assert not board.panel.visible
    screen._toggle_challenge_board()
    assert board.panel.visible and screen.board_button.content == "Fechar lousa"
    assert board.panel in list(walk(screen.overlay))
    _choose(screen, correct=True)
    assert not board.panel.visible  # após responder, a lousa dá lugar à correção
    assert not screen.board_button.visible


def test_answer_can_only_be_given_once(shell: GameShell) -> None:
    screen = _duel(shell)
    _find_pair(screen)
    _choose(screen, correct=False)
    first_feedback = screen.challenge_feedback
    _choose(screen, correct=True)
    assert screen.challenge_feedback == first_feedback


def test_resize_during_challenge_keeps_it(shell: GameShell) -> None:
    screen = _duel(shell)
    _find_pair(screen)
    question = screen.challenge.question
    screen.challenge_board.line_specs.append((0, 0, 5, 5, "#000000", 3.0))
    screen.challenge_board.stroke_starts.append(0)
    shell.page.resize(900, 1000)  # type: ignore[attr-defined]
    assert screen.overlay.visible and screen.challenge.question == question
    assert len(screen.challenge_board.line_specs) == 1


def test_duel_result_reports_challenges(shell: GameShell) -> None:
    screen = _duel(shell)
    page: FakePage = shell.page  # type: ignore[assignment]
    while not screen.game.is_complete:
        _find_pair(screen)
        if screen.challenge is not None:
            _choose(screen, correct=True)
            screen._close_challenge()
    texts = _texts(page.dialogs[-1])
    assert any("Desafios certos" in t and "Ana: 7/7" in t for t in texts)


def test_solo_never_shows_the_challenge(shell: GameShell) -> None:
    _home(shell)._play()
    screen = _memory(shell)
    _find_pair(screen)
    assert not screen.overlay.visible and screen.challenge is None


# ------------------------------------------------------------------ Nível 2
def test_level2_opens_and_returns_to_menu(shell: GameShell) -> None:
    _home(shell).on_level2()
    level2 = shell.current
    assert isinstance(level2, MemoryFinanceApp)
    back = next(c for c in walk(shell.page.controls[-1]) if isinstance(c, ft.TextButton) and c.content == "Menu inicial")
    back.on_click(None)
    assert isinstance(shell.current, HomeScreen)
    assert shell.page.on_resize == shell.current.on_resize
