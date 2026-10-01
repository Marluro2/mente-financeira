"""Modo administrador (MENTE_ADMIN=1)."""

import asyncio
from pathlib import Path
import random
from types import SimpleNamespace

import flet as ft
import pytest

from fakes import FakePage, walk
from mente_financeira.admin import admin_ativo
from mente_financeira.core.memory_game import Mode
from mente_financeira.storage import SettingsStore, default_data_dir
from mente_financeira.ui import memory_screen as memory_module
from mente_financeira.ui.admin_screen import CHALLENGES, CONCEPTS, LEVEL2, AdminScreen
from mente_financeira.ui.app import MemoryFinanceApp
from mente_financeira.ui.home import HomeScreen
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.shell import GameShell

PHONE, DESKTOP = (360, 740), (1280, 720)


@pytest.fixture(autouse=True)
def _no_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory_module, "MISMATCH_DELAY_SECONDS", 0)
    monkeypatch.setattr(memory_module, "RESULT_DELAY_SECONDS", 0)


@pytest.fixture
def admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MENTE_ADMIN", "1")


def _shell(tmp_path: Path, size=DESKTOP) -> GameShell:
    return GameShell(FakePage(*size), store=SettingsStore(tmp_path), rng=random.Random(4))  # type: ignore[arg-type]


def _texts(control: ft.Control) -> list[str]:
    return [c.value for c in walk(control) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def test_admin_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MENTE_ADMIN", raising=False)
    assert not admin_ativo()
    monkeypatch.setenv("MENTE_ADMIN", "1")
    assert admin_ativo()


def test_admin_settings_are_kept_apart(admin, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    assert default_data_dir() == tmp_path / "admin"


def test_regular_home_has_no_admin_panel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MENTE_ADMIN", raising=False)
    shell = _shell(tmp_path)
    assert "MODO ADMINISTRADOR" not in _texts(shell.page.controls[-1])
    assert shell.current.on_admin is None


@pytest.mark.parametrize("size", [PHONE, DESKTOP], ids=["celular", "computador"])
def test_admin_home_shows_banner_and_panel(admin, tmp_path: Path, size) -> None:
    shell = _shell(tmp_path, size)
    texts = _texts(shell.page.controls[-1])
    assert "MODO ADMINISTRADOR" in texts and "Painel do professor" in texts
    shell.current.on_admin()
    assert isinstance(shell.current, AdminScreen)


def test_admin_panel_tabs(admin, tmp_path: Path) -> None:
    shell = _shell(tmp_path)
    shell.open_admin()
    panel: AdminScreen = shell.current  # type: ignore[assignment]
    page = shell.page

    # Conceitos: navegação circular, na ordem do banco
    first = panel.deck.concepts[0]
    assert first.example in _texts(page.controls[-1])
    panel._previous_concept()
    assert panel.concept_index == len(panel.deck.concepts) - 1
    panel._next_concept()
    assert panel.concept_index == 0

    # Desafios: gabarito visível
    panel._select_tab(SimpleNamespace(control=SimpleNamespace(data=CHALLENGES)))
    texts = _texts(page.controls[-1])
    assert "✓ GABARITO" in texts and panel.challenge.explanation in texts
    panel._choose_kind(SimpleNamespace(control=SimpleNamespace(data=1)))
    assert "desconto" in panel.challenge.question

    # Nível 2: todos os cenários da fase, com resolução
    panel._select_tab(SimpleNamespace(control=SimpleNamespace(data=LEVEL2)))
    panel._choose_phase(SimpleNamespace(control=SimpleNamespace(value="7")))
    phase = panel.track.phases[7]
    texts = _texts(page.controls[-1])
    for scenario in phase.scenarios:
        pair = phase.render(scenario)
        assert pair.question in texts and f"✓ {pair.resolution}" in texts

    panel._select_tab(SimpleNamespace(control=SimpleNamespace(data=CONCEPTS)))
    assert panel.tab == CONCEPTS


def test_admin_memory_has_no_clock_and_shows_answers(admin, tmp_path: Path) -> None:
    shell = _shell(tmp_path)
    shell.play_memory(Mode.SOLO, ("Prof", None))
    screen: MemoryScreen = shell.current  # type: ignore[assignment]
    page: FakePage = shell.page  # type: ignore[assignment]
    assert not any(handler == screen._clock for handler, _ in page.tasks)
    assert "MODO ADMINISTRADOR" in _texts(page.controls[-1])

    images_before = [c.src for c in walk(page.controls[-1]) if isinstance(c, ft.Image)]
    assert images_before.count(screen.game.deck.back_image) == 16
    screen._toggle_answers()
    fronts = [sw.content for sw in screen.switchers]
    assert not any(isinstance(f, ft.Image) and f.src == screen.game.deck.back_image for f in fronts)
    assert screen.game.moves == 0 and not screen.game.matched  # não conta como jogada
    screen._toggle_answers()
    assert all(isinstance(sw.content, ft.Image) for sw in screen.switchers)


def test_admin_challenge_shows_answer_before_choosing(admin, tmp_path: Path) -> None:
    shell = _shell(tmp_path)
    shell.play_memory(Mode.DUEL, ("Ana", "Bruno"))
    screen: MemoryScreen = shell.current  # type: ignore[assignment]
    cards = screen.game.cards
    pair = next(i for i in range(1, 16) if cards[i].id == cards[0].id)
    for index in (0, pair):
        asyncio.run(screen._on_card_click(SimpleNamespace(control=SimpleNamespace(data=index))))
    assert screen.challenge is not None
    assert any(f"Gabarito: {screen.challenge.answer}" in t for t in _texts(screen.overlay))


def test_admin_level2_has_no_timer(admin, tmp_path: Path) -> None:
    shell = _shell(tmp_path)
    shell.open_level2()
    level2: MemoryFinanceApp = shell.current  # type: ignore[assignment]
    level2.session.set_players("A", "B")
    level2._begin_game()
    assert level2.timer_future is None
    assert level2.timer_text.value == "sem limite"
    assert "MODO ADMINISTRADOR" in _texts(shell.page.controls[-1])
    shell.show_home()
    assert isinstance(shell.current, HomeScreen)
