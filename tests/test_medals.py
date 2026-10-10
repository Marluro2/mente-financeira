"""Medalhas: metas de cada partida, gravação no aparelho e telas."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import json
from pathlib import Path
import random
from types import SimpleNamespace

import flet as ft
import pytest

from fakes import FakePage, started_shell, walk
from mente_financeira.core import engineering_challenge
from mente_financeira.core.medals import BY_KEY, MEDALS, NPV_LABEL, TRACK_MEDALS, GameSummary, MedalBook, new_medals
from mente_financeira.content.memory_deck import load_memory_deck
from mente_financeira.core.memory_game import MemoryGame, Mode
from mente_financeira.storage import Settings, SettingsStore
from mente_financeira.ui import memory_screen as memory_module
from mente_financeira.ui import tracks
from mente_financeira.ui.home import HomeScreen
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.shell import GameShell

BASE = GameSummary(
    track=tracks.FUNDAMENTAL,
    mode=Mode.SOLO,
    pairs=8,
    moves=20,
    stars=1,
    mistakes=12,
    elapsed=200,
    best_streak=1,
    points=(90,),
    challenges=((3, 7),),
)


def _keys(summary: GameSummary, owned: tuple[str, ...] = ()) -> list[str]:
    return [medal.key for medal in new_medals(summary, owned)]


# ====================================================================== metas
def test_first_game_gives_the_first_medal_and_the_track_one() -> None:
    assert _keys(BASE) == ["primeira_partida", "trilha_fundamental"]
    assert _keys(BASE, ("primeira_partida", "trilha_fundamental")) == []  # não repete


def test_solo_goals() -> None:
    great = replace(BASE, moves=10, stars=3, mistakes=2, elapsed=90, best_streak=5, points=(150,), challenges=((7, 7),))
    assert set(_keys(great)) >= {
        "tres_estrelas",
        "memoria_elefante",
        "foguete",
        "pegando_fogo",
        "imparavel",
        "genio_calculos",
        "cofrinho_cheio",
    }
    almost = replace(BASE, stars=2, mistakes=3, elapsed=91, best_streak=2, points=(149,), challenges=((6, 7),))
    assert _keys(almost) == ["primeira_partida", "trilha_fundamental"]


def test_all_right_needs_at_least_three_challenges() -> None:
    assert "genio_calculos" not in _keys(replace(BASE, challenges=((2, 2),)))
    assert "genio_calculos" in _keys(replace(BASE, challenges=((3, 3),)))


def test_duel_goals_count_for_either_player_but_not_solo_ones() -> None:
    duel = replace(BASE, mode=Mode.DUEL, stars=0, mistakes=0, elapsed=10, points=(40, 160), challenges=((1, 2), (4, 4)))
    keys = _keys(duel)
    assert {"duelo", "cofrinho_cheio", "genio_calculos"} <= set(keys)
    assert not {"tres_estrelas", "memoria_elefante", "foguete"} & set(keys)


def test_npv_medal_comes_from_a_right_npv_challenge() -> None:
    challenge = engineering_challenge._npv(random.Random(1))
    assert challenge.label == NPV_LABEL
    engineering = replace(BASE, track=tracks.ENGENHARIA, right_labels=frozenset({NPV_LABEL}))
    assert "primeiro_vpl" in _keys(engineering)
    assert "primeiro_vpl" not in _keys(replace(engineering, right_labels=frozenset({"PAYBACK"})))


def test_all_tracks_medal_arrives_with_the_third_track() -> None:
    assert set(TRACK_MEDALS) == {tracks.FUNDAMENTAL_1, tracks.FUNDAMENTAL, tracks.ENGENHARIA}
    owned = ("primeira_partida", TRACK_MEDALS[tracks.FUNDAMENTAL_1], TRACK_MEDALS[tracks.FUNDAMENTAL])
    assert _keys(replace(BASE, track=tracks.ENGENHARIA), owned) == ["trilha_engenharia", "todas_trilhas"]
    assert "todas_trilhas" not in _keys(replace(BASE, track=tracks.ENGENHARIA), owned[:2])


def test_medals_are_unique_and_described() -> None:
    assert len(BY_KEY) == len(MEDALS)
    for medal in MEDALS:
        assert medal.title and medal.goal.endswith(".") and medal.emoji


# ====================================================================== gravação
def test_book_saves_only_medal_keys_with_the_preferences(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path)
    store.save(Settings(palette="neon", sound=False))
    book = MedalBook(store)
    assert book.owned() == []
    won = book.record(BASE)
    assert [m.key for m in won] == ["primeira_partida", "trilha_fundamental"]
    assert book.record(BASE) == []
    saved = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert saved == {"palette": "neon", "dark_mode": False, "sound": False, "medals": ["primeira_partida", "trilha_fundamental"]}
    assert [m.key for m in book.owned()] == ["primeira_partida", "trilha_fundamental"]


def test_broken_medal_list_is_cleaned(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text(json.dumps({"medals": ["foguete", 3, None, "foguete"]}), encoding="utf-8")
    assert SettingsStore(tmp_path).load().medals == ["foguete"]
    (tmp_path / "settings.json").write_text(json.dumps({"medals": "foguete"}), encoding="utf-8")
    assert SettingsStore(tmp_path).load().medals == []


# ====================================================================== telas
@pytest.fixture(autouse=True)
def _no_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory_module, "MISMATCH_DELAY_SECONDS", 0)
    monkeypatch.setattr(memory_module, "RESULT_DELAY_SECONDS", 0)


@pytest.fixture(params=[(360, 740), (1280, 720)], ids=["celular", "computador"])
def shell(request: pytest.FixtureRequest, tmp_path: Path) -> GameShell:
    return started_shell(FakePage(*request.param), store=SettingsStore(tmp_path), rng=random.Random(4))  # type: ignore[arg-type]


def _texts(control: ft.Control) -> list[str]:
    return [c.value for c in walk(control) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def _play_perfect_solo(shell: GameShell) -> MemoryScreen:
    home = shell.current
    assert isinstance(home, HomeScreen)
    home._play()
    screen = shell.current
    assert isinstance(screen, MemoryScreen)
    cards = screen.game.cards
    for index in range(len(cards)):
        if screen.game.is_revealed(index):
            continue
        pair = next(i for i, c in enumerate(cards) if i != index and c.id == cards[index].id)
        for i in (index, pair):
            asyncio.run(screen._on_card_click(SimpleNamespace(control=SimpleNamespace(data=i))))
        if screen.challenge is not None:
            screen._answer_challenge(SimpleNamespace(control=SimpleNamespace(data=screen.challenge.answer_index)))
            screen._close_challenge()
    return screen


def test_result_shows_new_medals_and_home_counts_them(shell: GameShell) -> None:
    home = shell.current
    assert isinstance(home, HomeScreen)
    assert f"0/{len(MEDALS)}" in " ".join(str(b.content) for b in walk(shell.page.controls[-1]) if isinstance(b, ft.TextButton))

    _play_perfect_solo(shell)
    result = shell.page.dialogs[-1]  # type: ignore[attr-defined]
    texts = _texts(result)
    won = [m for m in MEDALS if m.title in texts]
    assert any(t.startswith("🏅") for t in texts)
    assert {m.key for m in won} >= {"primeira_partida", "tres_estrelas", "imparavel", "genio_calculos", "cofrinho_cheio", "trilha_fundamental"}

    shell.show_home()
    home = shell.current
    assert isinstance(home, HomeScreen)
    count = f"{len(won)}/{len(MEDALS)}"
    labels = [str(b.content) for b in walk(shell.page.controls[-1]) if isinstance(b, ft.TextButton)]
    assert any(count in label for label in labels)

    home._open_medals()
    dialog = shell.page.dialogs[-1]  # type: ignore[attr-defined]
    assert f"{len(won)} de {len(MEDALS)}" in _texts(dialog)
    assert all(m.title in _texts(dialog) for m in MEDALS)  # as que faltam aparecem, apagadas


def test_second_game_does_not_repeat_medals(shell: GameShell) -> None:
    _play_perfect_solo(shell)
    shell.show_home()
    _play_perfect_solo(shell)
    texts = _texts(shell.page.dialogs[-1])  # type: ignore[attr-defined]
    assert not any(t.startswith("🏅") for t in texts)


def test_online_duel_gives_no_medals() -> None:
    page = FakePage(390, 844)
    game = MemoryGame(load_memory_deck(), random.Random(1))
    game.new_game(Mode.DUEL, ("Ana", "Bia"))
    called: list[str] = []
    screen = MemoryScreen(
        page,  # type: ignore[arg-type]
        game,
        on_home=lambda: None,
        on_level2=lambda: None,
        online=SimpleNamespace(seat=0, changed=lambda: None),  # type: ignore[arg-type]
        medals=lambda g, labels: called.append("medalhas") or [],
    )
    screen._show_result()
    assert called == []

