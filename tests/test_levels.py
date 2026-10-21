"""Escolha do nível da Engenharia de Produção (entre as trilhas e o modo de jogo)."""

from pathlib import Path
import random
from types import SimpleNamespace

import flet as ft
import pytest

from fakes import FakePage, walk
from mente_financeira.core.engineering_challenge import ENGINEERING_LEVEL_KITS
from mente_financeira.core.memory_game import Mode
from mente_financeira.storage import SettingsStore
from mente_financeira.ui import style
from mente_financeira.ui.home import HomeScreen
from mente_financeira.ui.levels import LEVELS, LevelsScreen
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.shell import GameShell
from mente_financeira.ui.tracks import ENGENHARIA, FUNDAMENTAL, TracksScreen

PHONE, NOTEBOOK, DESKTOP = (360, 740), (1536, 785), (1920, 1000)


@pytest.fixture(autouse=True)
def default_theme():
    yield
    style.apply_theme(style.DEFAULT_THEME)


@pytest.fixture(params=[PHONE, NOTEBOOK, DESKTOP], ids=["celular", "notebook", "computador"])
def shell(request: pytest.FixtureRequest, tmp_path: Path) -> GameShell:
    shell = GameShell(FakePage(*request.param), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    shell.open_track(ENGENHARIA)
    return shell


def _texts(control: ft.Control) -> list[str]:
    return [c.value for c in walk(control) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def _button(control: ft.Control, label: str) -> ft.TextButton:
    return next(c for c in walk(control) if isinstance(c, ft.TextButton) and c.content == label)


def _hover(screen: LevelsScreen, key: str | None) -> None:
    target = key or LEVELS[0].key
    button = next(c for c in walk(screen.page.controls[-1]) if isinstance(c, ft.Container) and c.data == target)
    screen._hover_level(SimpleNamespace(control=button, data="true" if key else "false"))


def test_engineering_shows_the_three_levels_and_floating_topics(shell: GameShell) -> None:
    screen = shell.current
    assert isinstance(screen, LevelsScreen)
    texts = _texts(shell.page.controls[-1])
    for title in ("Fundamentos financeiros e de custos", "Avaliação de investimentos", "Operações e tomada de decisão"):
        assert title in texts
    for topic in ("TIR", "VPL", "Fluxo de caixa", "Ponto de equilíbrio"):
        assert topic in texts
    assert len(screen.topics) == sum(len(level.topics) for level in LEVELS)
    assert shell.page.on_resize == screen.on_resize


def test_hovering_a_level_lights_up_its_topics(shell: GameShell) -> None:
    screen: LevelsScreen = shell.current  # type: ignore[assignment]
    _hover(screen, "nivel2")
    lit = {t.text for t in screen.topics if t.box.opacity == 1}
    assert lit == {"Payback", "VPL", "TIR", "TMA", "Risco", "Financiamento"}
    assert "NÍVEL 2" in screen.caption.value
    _hover(screen, None)
    assert screen.highlight is None
    assert all(t.box.opacity == 0.95 for t in screen.topics)


@pytest.mark.parametrize("key", [level.key for level in LEVELS])
def test_every_level_opens_the_game_with_its_name(shell: GameShell, key: str) -> None:
    shell.current._choose(SimpleNamespace(control=SimpleNamespace(data=key)))  # type: ignore[union-attr]
    home = shell.current
    assert isinstance(home, HomeScreen)
    texts = _texts(shell.page.controls[-1])
    number = next(level.number for level in LEVELS if level.key == key)
    assert any(text.startswith(f"Nível {number}") for text in texts)
    assert "Como você quer jogar?" in texts
    # "Níveis" volta para a escolha do nível, que volta para as trilhas.
    _button(shell.page.controls[-1], "Níveis").on_click(None)
    assert isinstance(shell.current, LevelsScreen)
    _button(shell.page.controls[-1], "Trilhas").on_click(None)
    assert isinstance(shell.current, TracksScreen)


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.key)
def test_each_level_plays_with_its_own_cards_and_questions(shell: GameShell, level) -> None:
    shell.current._choose(SimpleNamespace(control=SimpleNamespace(data=level.key)))  # type: ignore[union-attr]
    shell.play_memory(Mode.SOLO, ("Ana", None))
    screen = shell.current
    assert isinstance(screen, MemoryScreen)
    assert {c.level for c in screen.game.cards} == {level.number}  # TIR não aparece no Nível 1
    assert screen.challenges is ENGINEERING_LEVEL_KITS[level.number]
    assert f"Nível {level.number} • Modo Solo" in _texts(shell.page.controls[-1])


def test_other_tracks_skip_the_levels_page(tmp_path: Path) -> None:
    shell = GameShell(FakePage(1280, 720), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    shell.open_track(FUNDAMENTAL)
    assert isinstance(shell.current, HomeScreen)
    _button(shell.page.controls[-1], "Trilhas")  # o botão continua "Trilhas"


def test_phone_highlight_moves_by_itself(tmp_path: Path) -> None:
    import asyncio

    shell = GameShell(FakePage(*PHONE), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    shell.open_track(ENGENHARIA)
    screen: LevelsScreen = shell.current  # type: ignore[assignment]
    seen = []

    async def fake_sleep(_: float) -> None:
        seen.append(screen.highlight)
        if len(seen) >= 5:
            screen.stop()

    original = asyncio.sleep
    asyncio.sleep = fake_sleep  # type: ignore[assignment]
    try:
        asyncio.run(screen._float_loop(screen.generation))
    finally:
        asyncio.sleep = original
    assert seen[0] is LEVELS[0] and LEVELS[1] in seen  # passa de um nível para o outro


def test_levels_page_follows_the_theme(tmp_path: Path) -> None:
    shell = GameShell(FakePage(1280, 720), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    shell.choose_theme("floresta")
    shell.open_track(ENGENHARIA)
    background = shell.page.controls[-1].content.gradient
    assert background.colors[0] == style.theme_by_key("floresta").background[0]
