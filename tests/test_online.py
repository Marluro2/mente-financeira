"""Modo online: sala de espera, duelo entre duas telas e contagem por trilha."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
import random
from types import SimpleNamespace
from typing import Any

import flet as ft
import pytest

from fakes import FakePage, walk
from mente_financeira.content.memory_deck import load_memory_deck
from mente_financeira.online import status
from mente_financeira.online.app import OnlineApp, SessionStore, new_lobby, track_from_route
from mente_financeira.online.lobby import Lobby, NicknameError, clean_nickname
from mente_financeira.storage import Settings, SettingsStore
from mente_financeira.ui import memory_screen as memory_module
from mente_financeira.ui.home import HomeScreen
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.shell import GameShell
from mente_financeira.ui.tracks import FUNDAMENTAL, FUNDAMENTAL_1, MEDIO, TracksScreen

Handler = Callable[[dict[str, Any]], Awaitable[None]]


@pytest.fixture(autouse=True)
def _no_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory_module, "MISMATCH_DELAY_SECONDS", 0)
    monkeypatch.setattr(memory_module, "RESULT_DELAY_SECONDS", 0)


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


def _lobby() -> Lobby:
    lobby = new_lobby()
    lobby.rng = random.Random(3)
    return lobby


def _texts(page: FakePage) -> list[str]:
    return [c.value for c in walk(page.controls[-1]) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def _join(hub: FakeHub, lobby: Lobby, player_id: str, track: str | None = FUNDAMENTAL) -> OnlineApp:
    return OnlineApp(FakePage(1280, 720), lobby, hub.messenger(player_id), player_id=player_id, track=track)  # type: ignore[arg-type]


def _search(app: OnlineApp, hub: FakeHub, nickname: str) -> None:
    app.name_field.value = nickname
    app._search()
    hub.flush()


def _pair(hub: FakeHub, lobby: Lobby) -> tuple[OnlineApp, OnlineApp]:
    ana, bia = _join(hub, lobby, "a"), _join(hub, lobby, "b")
    _search(ana, hub, "Ana")
    _search(bia, hub, "Bia")
    return ana, bia


def _tap(app: OnlineApp, index: int) -> None:
    assert app.game_screen is not None
    asyncio.run(app.game_screen._on_card_click(SimpleNamespace(control=SimpleNamespace(data=index))))


def _pair_of(game: Any, index: int) -> int:
    return next(i for i, c in enumerate(game.cards) if i != index and c.id == game.cards[index].id)


def _mismatch(game: Any) -> tuple[int, int]:
    first = 0
    return first, next(i for i, c in enumerate(game.cards) if c.id != game.cards[first].id)


# ------------------------------------------------------------------ sala (regras)
def test_nickname_is_trimmed_and_limited() -> None:
    assert clean_nickname("  Lia   Souza ") == "Lia Souza"
    for bad in ("", " a ", "x" * 17, None):
        with pytest.raises(NicknameError):
            clean_nickname(bad)


def test_lobby_pairs_two_people_on_the_same_track_only() -> None:
    lobby = _lobby()
    assert lobby.wait("a", "Ana", FUNDAMENTAL) is None
    assert lobby.wait("c", "Caio", FUNDAMENTAL_1) is None  # outra trilha: continua esperando
    match = lobby.wait("b", "Bia", FUNDAMENTAL)
    assert match is not None and [p.nickname for p in match.players] == ["Ana", "Bia"]
    assert match.game.players == ["Ana", "Bia"] and match.game.active
    assert lobby.matches["a"] is lobby.matches["b"] is match
    assert lobby.counts() == {FUNDAMENTAL_1: 1, FUNDAMENTAL: 2}
    with pytest.raises(ValueError):
        lobby.wait("d", "Duda", MEDIO)  # trilha ainda sem jogo


def test_leaving_forgets_the_player() -> None:
    lobby = _lobby()
    lobby.wait("a", "Ana", FUNDAMENTAL)
    lobby.leave("a")
    assert lobby.counts() == {FUNDAMENTAL_1: 0, FUNDAMENTAL: 0}
    assert not lobby.waiting and not lobby.matches and not lobby.browsing
    match = lobby.wait("b", "Bia", FUNDAMENTAL)
    assert match is None  # a Ana já tinha saído


def test_tracks_use_their_own_decks() -> None:
    lobby = _lobby()
    lobby.wait("a", "Ana", FUNDAMENTAL_1)
    match = lobby.wait("b", "Bia", FUNDAMENTAL_1)
    assert match is not None
    ids = {c.id for c in load_memory_deck("memoria_fundamental1").concepts}
    assert {c.id for c in match.game.cards} <= ids


# ------------------------------------------------------------------ sala (tela)
def test_lobby_screen_asks_only_for_a_nickname_and_shows_counts() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana = _join(hub, lobby, "a", track="qualquer")
    assert ana.track == FUNDAMENTAL  # trilha desconhecida no endereço: usa a padrão
    texts = _texts(ana.page)
    assert "Ensino Fundamental 1" in texts and "Ensino Fundamental 2" in texts
    assert "Ensino Médio" not in texts
    assert ana.name_field.label == "Seu apelido" and ana.name_field.max_length == 16
    assert any("Nada fica guardado" in t for t in texts)
    assert ana.count_labels[FUNDAMENTAL].value == "1 pessoa online"

    _join(hub, lobby, "b", track=FUNDAMENTAL)
    hub.flush()
    assert ana.count_labels[FUNDAMENTAL].value == "2 pessoas online"


def test_track_from_the_site_link_is_preselected() -> None:
    ana = _join(FakeHub(), _lobby(), "a", track=FUNDAMENTAL_1)
    assert ana.track == FUNDAMENTAL_1 and ana.lobby.browsing == {"a": FUNDAMENTAL_1}


def test_short_nickname_shows_an_error() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana = _join(hub, lobby, "a")
    _search(ana, hub, "A")
    assert ana.name_field.error and not lobby.waiting


def test_waiting_screen_and_cancel() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana = _join(hub, lobby, "a")
    _search(ana, hub, "Ana")
    assert lobby.is_waiting("a")
    assert "Olá, Ana! Esperando alguém para jogar" in _texts(ana.page)
    ana._cancel()
    assert not lobby.is_waiting("a") and ana.name_field.value == "Ana"


# ------------------------------------------------------------------ duelo
def test_second_player_starts_the_match_on_both_screens() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana, bia = _pair(hub, lobby)
    assert isinstance(ana.game_screen, MemoryScreen) and isinstance(bia.game_screen, MemoryScreen)
    assert ana.game_screen.game is bia.game_screen.game
    assert (ana.game_screen.online.seat, bia.game_screen.online.seat) == (0, 1)
    assert "Nível 1 • Duelo online" in _texts(ana.page)
    # Só a tela de quem começa conta o tempo; não há "nova partida" online.
    assert any(task[0] == ana.game_screen._clock for task in ana.page.tasks)
    assert not any(task[0] == bia.game_screen._clock for task in bia.page.tasks)
    assert not any(isinstance(c, ft.IconButton) and c.tooltip == "Nova partida" for c in walk(ana.page.controls[-1]))


def test_only_the_player_on_turn_can_flip() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana, bia = _pair(hub, lobby)
    game = ana.game_screen.game
    _tap(bia, 0)
    assert game.face_up == [] and "Espere: agora é a vez de Ana." in _texts_of_dialogs(bia.page)


def _texts_of_dialogs(page: FakePage) -> list[str]:
    return [c.value for d in page.dialogs for c in walk(d) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def test_moves_show_up_on_the_opponent_screen_and_turn_passes() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana, bia = _pair(hub, lobby)
    game = ana.game_screen.game
    first, other = _mismatch(game)
    _tap(ana, first)
    hub.flush()
    image = bia.game_screen.cards[first]
    assert game.face_up == [first] and image is not None
    _tap(ana, other)
    hub.flush()
    assert game.turn == 1 and game.moves == 1
    assert "Sua vez! 🎯" in _texts_of_dialogs(bia.page)
    _tap(ana, 2)
    assert game.face_up == []  # agora é a vez da Bia


def test_pair_and_challenge_keep_both_screens_in_sync() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana, bia = _pair(hub, lobby)
    game = ana.game_screen.game
    _tap(ana, 0)
    _tap(ana, _pair_of(game, 0))
    hub.flush()
    assert game.awaiting_challenge and ana.game_screen.challenge is not None
    assert bia.game_screen.challenge is None  # o desafio aparece só para quem joga
    assert "Ana está no Desafio Relâmpago..." in _texts_of_dialogs(bia.page)
    assert bia.game_screen.seen_learned == 1  # a Bia também vê o conceito aprendido
    screen = ana.game_screen
    wrong = (screen.challenge.answer_index + 1) % len(screen.challenge.options)
    screen._answer_challenge(SimpleNamespace(control=SimpleNamespace(data=wrong)))
    screen._close_challenge()
    hub.flush()
    assert game.turn == 1 and "Sua vez! 🎯" in _texts_of_dialogs(bia.page)


def test_finishing_shows_the_result_on_both_screens() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana, bia = _pair(hub, lobby)
    game = ana.game_screen.game
    while not game.is_complete:
        app = ana if game.turn == 0 else bia
        first = next(i for i in range(len(game.cards)) if i not in game.matched)
        _tap(app, first)
        _tap(app, _pair_of(game, first))
        if app.game_screen.challenge is not None:
            screen = app.game_screen
            screen._answer_challenge(SimpleNamespace(control=SimpleNamespace(data=screen.challenge.answer_index)))
            screen._close_challenge()
        hub.flush()
    assert ana.game_screen.result_shown and bia.game_screen.result_shown
    result = next(d for d in bia.page.dialogs if isinstance(d, ft.AlertDialog) and d.title.value == "Mandou bem! 🎉")
    assert [b.content for b in result.actions] == ["Voltar à sala"]


def test_opponent_leaving_ends_the_match_and_forgets_both() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana, bia = _pair(hub, lobby)
    ana.close()  # Ana fechou a página
    hub.flush()
    dialog = bia.page.dialogs[-1]
    assert dialog.title.value == "Partida encerrada"
    assert "Ana saiu da partida." in [c.value for c in walk(dialog) if isinstance(c, ft.Text)]
    next(b for b in dialog.actions if b.content == "Voltar à sala").on_click(None)
    hub.flush()
    assert bia.game_screen is None and "Escolha a trilha" in _texts(bia.page)
    assert not lobby.matches and lobby.counts()[FUNDAMENTAL] == 1  # só a Bia, na sala
    assert all(owner != "a" for handlers in hub.handlers.values() for owner, _ in handlers)
    bia.close()
    assert lobby.counts() == {FUNDAMENTAL_1: 0, FUNDAMENTAL: 0}


def test_sound_preference_stays_in_memory(tmp_path: Path) -> None:
    store = SessionStore()
    store.path = tmp_path / "settings.json"
    store.save(Settings(sound=False))
    assert store.load().sound is False and not store.path.exists()


# ------------------------------------------------------------------ site
def test_online_is_hidden_until_there_is_a_server(tmp_path: Path) -> None:
    assert status.SERVER_URL == "" and not status.online_enabled()
    shell = GameShell(FakePage(1280, 720), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    assert shell.current.fetch_online is None and not shell.current.online_labels
    shell.open_track(FUNDAMENTAL)
    assert isinstance(shell.current, HomeScreen) and shell.current.online_url is None


def test_home_has_play_online_button_when_server_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(status, "SERVER_URL", "https://exemplo.onrender.com/")
    shell = GameShell(FakePage(1280, 720), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    shell.open_track(FUNDAMENTAL_1)
    home = shell.current
    assert home.online_url == "https://exemplo.onrender.com/?trilha=fundamental1"
    button = next(c for c in walk(shell.page.controls[-1]) if isinstance(c, ft.OutlinedButton))
    button.on_click(None)
    assert shell.page.tasks[-1] == (shell.page.launch_url, (home.online_url,))


def test_tracks_page_shows_who_is_online(tmp_path: Path) -> None:
    async def fetch() -> dict[str, int]:
        return {FUNDAMENTAL_1: 0, FUNDAMENTAL: 3}

    page = FakePage(1280, 720)
    screen = TracksScreen(page, load_memory_deck(), on_select=lambda _: None, fetch_online=fetch)  # type: ignore[arg-type]
    screen.show()
    assert set(screen.online_labels) == {FUNDAMENTAL_1, FUNDAMENTAL}  # só trilhas abertas
    assert not any(label.visible for label in screen.online_labels.values())  # ainda sem resposta
    loop = next(task for task in page.tasks if task[0] == screen._online_loop)

    async def one_round() -> None:
        runner = asyncio.create_task(loop[0](*loop[1]))
        await asyncio.sleep(0)
        screen.stop()
        runner.cancel()

    asyncio.run(one_round())
    assert screen.online_labels[FUNDAMENTAL].value == "🟢 3 online agora"
    assert screen.online_labels[FUNDAMENTAL_1].value == "⚪ Ninguém online agora"
    assert all(label.visible for label in screen.online_labels.values())


def test_counts_parsing_and_offline_server() -> None:
    assert status.parse_counts({"fundamental": 2, "x": -1, "y": "3"}) == {"fundamental": 2}
    assert status.parse_counts([1, 2]) == {}
    assert status.play_url(FUNDAMENTAL, "https://a.b/") == "https://a.b/?trilha=fundamental"
    assert asyncio.run(status.fetch_counts("http://127.0.0.1:9")) is None  # servidor fora do ar


def test_track_comes_from_the_address() -> None:
    assert track_from_route("/?trilha=fundamental1") == FUNDAMENTAL_1
    assert track_from_route("/") is None and track_from_route(None) is None
