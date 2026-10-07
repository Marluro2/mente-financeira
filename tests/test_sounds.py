"""Efeitos sonoros: arquivos, momentos em que tocam e botão liga/desliga."""

import asyncio
from pathlib import Path
import random
from types import SimpleNamespace
import wave

import pytest

from fakes import FakePage, started_shell
from mente_financeira.core.memory_game import Mode
from mente_financeira.storage import Settings, SettingsStore
from mente_financeira.ui import app as app_module
from mente_financeira.ui import memory_screen as memory_module
from mente_financeira.ui.app import MemoryFinanceApp
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.shell import GameShell
from mente_financeira.ui.sounds import SOUNDS

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "sons"


@pytest.fixture(autouse=True)
def _no_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory_module, "MISMATCH_DELAY_SECONDS", 0)
    monkeypatch.setattr(memory_module, "RESULT_DELAY_SECONDS", 0)
    monkeypatch.setattr(app_module, "REVEAL_DELAY_SECONDS", 0)


def _shell(tmp_path: Path) -> GameShell:
    return started_shell(FakePage(), store=SettingsStore(tmp_path), rng=random.Random(4))  # type: ignore[arg-type]


def _tap(screen: MemoryScreen, index: int) -> None:
    asyncio.run(screen._on_card_click(SimpleNamespace(control=SimpleNamespace(data=index))))


def _pair_of(screen: MemoryScreen, index: int) -> int:
    cards = screen.game.cards
    return next(i for i, c in enumerate(cards) if i != index and c.id == cards[index].id)


@pytest.mark.parametrize("name", SOUNDS)
def test_sound_files_are_short_valid_wavs(name: str) -> None:
    with wave.open(str(ASSETS / f"{name}.wav")) as wav:
        assert wav.getnchannels() == 1 and wav.getframerate() == 44_100
        assert 0.05 < wav.getnframes() / wav.getframerate() < 2.0


def test_sounds_are_loaded_once_into_the_page(tmp_path: Path) -> None:
    shell = _shell(tmp_path)
    assert len(shell.page.services) == len(SOUNDS)
    shell.play_memory(Mode.SOLO, ("Ana", None))
    shell.show_home()
    assert len(shell.page.services) == len(SOUNDS)


def test_memory_game_sounds(tmp_path: Path) -> None:
    shell = _shell(tmp_path)
    shell.play_memory(Mode.SOLO, ("Ana", None))
    screen: MemoryScreen = shell.current  # type: ignore[assignment]
    history = shell.sounds.history

    wrong = next(i for i, c in enumerate(screen.game.cards) if c.id != screen.game.cards[0].id)
    _tap(screen, 0)
    _tap(screen, wrong)
    assert history == ["virar", "virar", "erro"]

    history.clear()
    _tap(screen, 0)
    _tap(screen, _pair_of(screen, 0))
    assert history == ["virar", "virar", "acerto"]

    history.clear()
    for index in range(16):
        if not screen.game.is_revealed(index):
            _tap(screen, index)
            _tap(screen, _pair_of(screen, index))
    assert history[-1] == "vitoria"
    assert history.count("vitoria") == 1


def test_challenge_sounds(tmp_path: Path) -> None:
    shell = _shell(tmp_path)
    shell.play_memory(Mode.DUEL, ("Ana", "Bruno"))
    screen: MemoryScreen = shell.current  # type: ignore[assignment]
    _tap(screen, 0)
    _tap(screen, _pair_of(screen, 0))
    shell.sounds.history.clear()
    screen._answer_challenge(SimpleNamespace(control=SimpleNamespace(data=screen.challenge.answer_index)))
    assert shell.sounds.history == ["incentivo"]
    screen._close_challenge()

    index = next(i for i in range(16) if not screen.game.is_revealed(i))
    _tap(screen, index)
    _tap(screen, _pair_of(screen, index))
    shell.sounds.history.clear()
    screen._answer_challenge(SimpleNamespace(control=SimpleNamespace(data=(screen.challenge.answer_index + 1) % 4)))
    assert shell.sounds.history == ["erro"]


def test_level2_sounds(tmp_path: Path) -> None:
    shell = _shell(tmp_path)
    shell.open_level2()
    level2: MemoryFinanceApp = shell.current  # type: ignore[assignment]
    level2._begin_game()
    history = shell.sounds.history
    history.clear()

    session = level2.session

    def click(side: str, pid: str) -> None:
        asyncio.run(level2._on_card_click(SimpleNamespace(control=SimpleNamespace(data=(side, pid)))))

    first = session.question_order[0]
    wrong = next(p for p in session.resolution_order if p != first)
    click("question", first)
    click("resolution", wrong)
    assert history == ["virar", "virar", "erro"]

    history.clear()
    click("question", first)
    click("resolution", first)
    assert history == ["virar", "virar", "acerto"]

    for pid in list(session.question_order):
        if pid not in session.matched:
            click("question", pid)
            click("resolution", pid)
    level2._after_match_explanation()
    assert history[-1] == "vitoria"


def test_toggle_mutes_and_is_remembered_without_losing_theme(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path)
    store.save(Settings(palette="neon", dark_mode=True))
    shell = started_shell(FakePage(), store=store, rng=random.Random(1))  # type: ignore[arg-type]
    shell.play_memory(Mode.SOLO, (None, None))
    screen: MemoryScreen = shell.current  # type: ignore[assignment]

    shell.sounds.toggle()
    assert not shell.sounds.enabled
    assert store.load() == Settings(palette="neon", dark_mode=True, sound=False)
    shell.sounds.history.clear()
    _tap(screen, 0)
    assert shell.sounds.history == []  # silêncio

    again = started_shell(FakePage(), store=store)  # type: ignore[arg-type]
    assert not again.sounds.enabled  # lembrado na próxima vez
    again.sounds.toggle()
    assert store.load().sound and again.sounds.history == ["virar"]


def test_level2_theme_change_keeps_sound_choice(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path)
    store.save(Settings(sound=False))
    app = MemoryFinanceApp(FakePage(), store=store)  # type: ignore[arg-type]
    app._begin_game()
    app._change_palette(SimpleNamespace(control=SimpleNamespace(value="neon")))
    assert store.load() == Settings(palette="neon", dark_mode=False, sound=False)
