"""Duelo em sala: códigos de sala, duelo entre dois celulares e servidor sem internet."""

from __future__ import annotations

import asyncio
from pathlib import Path
import random
from types import SimpleNamespace
from typing import Any

import flet as ft
import pytest
from fastapi.testclient import TestClient

from fakes import FakeHub, FakePage, walk
from mente_financeira.content.memory_deck import load_memory_deck
from mente_financeira.sala.app import RoomApp, SessionStore, code_from_route, new_lobby, room_qr_path
from mente_financeira.sala.salas import ANIMALS, Lobby, NicknameError, RoomError, clean_nickname, normalize_code
from mente_financeira.storage import Settings
from mente_financeira.ui import memory_screen as memory_module
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.tracks import FUNDAMENTAL, FUNDAMENTAL_1, MEDIO
import servidor_sala


@pytest.fixture(autouse=True)
def _no_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory_module, "MISMATCH_DELAY_SECONDS", 0)
    monkeypatch.setattr(memory_module, "RESULT_DELAY_SECONDS", 0)


def _lobby() -> Lobby:
    lobby = new_lobby()
    lobby.rng = random.Random(3)
    return lobby


def _texts(page: FakePage) -> list[str]:
    return [c.value for c in walk(page.controls[-1]) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def _texts_of_dialogs(page: FakePage) -> list[str]:
    return [c.value for d in page.dialogs for c in walk(d) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def _join(hub: FakeHub, lobby: Lobby, player_id: str, code: str | None = None) -> RoomApp:
    return RoomApp(FakePage(390, 844), lobby, hub.messenger(player_id), player_id=player_id, code=code)  # type: ignore[arg-type]


def _create(app: RoomApp, hub: FakeHub, nickname: str) -> str:
    app.name_field.value = nickname
    app._create()
    hub.flush()
    room = app.lobby.room_of(app.player_id)
    assert room is not None
    return room.code


def _enter(app: RoomApp, hub: FakeHub, nickname: str, code: str) -> None:
    app.name_field.value, app.code_field.value = nickname, code
    app._join()
    hub.flush()


def _pair(hub: FakeHub, lobby: Lobby) -> tuple[RoomApp, RoomApp]:
    ana, bia = _join(hub, lobby, "a"), _join(hub, lobby, "b")
    code = _create(ana, hub, "Ana")
    _enter(bia, hub, "Bia", code)
    return ana, bia


def _tap(app: RoomApp, index: int) -> None:
    assert app.game_screen is not None
    asyncio.run(app.game_screen._on_card_click(SimpleNamespace(control=SimpleNamespace(data=index))))


def _pair_of(game: Any, index: int) -> int:
    return next(i for i, c in enumerate(game.cards) if i != index and c.id == game.cards[index].id)


def _mismatch(game: Any) -> tuple[int, int]:
    first = 0
    return first, next(i for i, c in enumerate(game.cards) if c.id != game.cards[first].id)


# ------------------------------------------------------------------ salas (regras)
def test_nickname_is_trimmed_and_limited() -> None:
    assert clean_nickname("  Lia   Souza ") == "Lia Souza"
    for bad in ("", " a ", "x" * 17, None):
        with pytest.raises(NicknameError):
            clean_nickname(bad)


def test_codes_are_easy_to_type() -> None:
    for raw in ("gato42", "Gato 42", "GATO-42", " gato - 42 "):
        assert normalize_code(raw) == "GATO-42"
    for bad in ("", "42", "GATO", "GATO-4", "GATO-421"):
        with pytest.raises(RoomError):
            normalize_code(bad)


def test_create_and_join_a_room() -> None:
    lobby = _lobby()
    room = lobby.create_room("a", "Ana", FUNDAMENTAL_1)
    word, number = room.code.split("-")
    assert word in ANIMALS and 10 <= int(number) <= 99
    match = lobby.join("b", "Bia", room.code.lower().replace("-", ""))
    assert [p.nickname for p in match.players] == ["Ana", "Bia"] and match.track == FUNDAMENTAL_1
    assert match.game.players == ["Ana", "Bia"] and match.game.active
    assert lobby.matches["a"] is lobby.matches["b"] is match and not lobby.rooms
    ids = {c.id for c in load_memory_deck("memoria_fundamental1").concepts}
    assert {c.id for c in match.game.cards} <= ids  # baralho da trilha de quem criou
    with pytest.raises(RoomError):
        lobby.join("c", "Caio", room.code)  # a sala já começou
    with pytest.raises(ValueError):
        lobby.create_room("d", "Duda", MEDIO)  # trilha ainda sem jogo


def test_wrong_code_and_own_room_are_refused() -> None:
    lobby = _lobby()
    room = lobby.create_room("a", "Ana", FUNDAMENTAL)
    with pytest.raises(RoomError, match="Não achei a sala"):
        lobby.join("b", "Bia", "ZEBRA-11" if room.code != "ZEBRA-11" else "PATO-12")
    with pytest.raises(RoomError, match="sua"):
        lobby.join("a", "Ana", room.code)


def test_codes_do_not_repeat() -> None:
    lobby = _lobby()
    codes = {lobby.create_room(str(i), "Jogador", FUNDAMENTAL).code for i in range(200)}
    assert len(codes) == 200


def test_leaving_forgets_the_player() -> None:
    lobby = _lobby()
    room = lobby.create_room("a", "Ana", FUNDAMENTAL)
    lobby.leave("a")
    assert not lobby.rooms and not lobby.matches
    with pytest.raises(RoomError):
        lobby.join("b", "Bia", room.code)


# ------------------------------------------------------------------ salas (tela)
def test_start_screen_asks_only_for_a_nickname() -> None:
    ana = _join(FakeHub(), _lobby(), "a")
    texts = _texts(ana.page)
    assert {"Criar uma sala", "Entrar numa sala", "Ensino Fundamental 1", "Ensino Fundamental 2"} <= set(texts)
    assert "Ensino Médio" not in texts
    assert texts.index("Criar uma sala") < texts.index("Entrar numa sala")
    assert ana.name_field.label == "Seu apelido" and ana.name_field.max_length == 16
    assert any("Nada fica guardado" in t for t in texts)


def test_qr_code_link_fills_the_room_code() -> None:
    assert code_from_route("/?sala=GATO-42") == "GATO-42" and code_from_route("/") is None
    bia = _join(FakeHub(), _lobby(), "b", code="GATO-42")
    texts = _texts(bia.page)
    assert bia.code_field.value == "GATO-42"
    assert texts.index("Entrar numa sala") < texts.index("Criar uma sala")  # entrar vem primeiro


def test_waiting_screen_shows_code_and_qr() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana = _join(hub, lobby, "a")
    ana._choose_track(SimpleNamespace(control=SimpleNamespace(data=FUNDAMENTAL_1)))
    code = _create(ana, hub, "Ana")
    texts = _texts(ana.page)
    assert code in texts and "Olá, Ana! Sua sala é:" in texts
    images = [c.src for c in walk(ana.page.controls[-1]) if isinstance(c, ft.Image)]
    assert room_qr_path(code) in images
    assert lobby.room_of("a").track == FUNDAMENTAL_1
    ana._cancel()
    assert not lobby.rooms and ana.name_field.value == "Ana"


def test_errors_show_on_the_fields() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana = _join(hub, lobby, "a")
    ana.name_field.value = "A"
    ana._create()
    assert ana.name_field.error and not lobby.rooms
    _enter(ana, hub, "Ana", "LOBO-77")
    assert "Não achei a sala LOBO-77" in ana.code_field.error and ana.game_screen is None


# ------------------------------------------------------------------ duelo
def test_second_player_starts_the_match_on_both_screens() -> None:
    hub, lobby = FakeHub(), _lobby()
    ana, bia = _pair(hub, lobby)
    assert isinstance(ana.game_screen, MemoryScreen) and isinstance(bia.game_screen, MemoryScreen)
    assert ana.game_screen.game is bia.game_screen.game
    assert (ana.game_screen.online.seat, bia.game_screen.online.seat) == (0, 1)
    assert "Nível 1 • Duelo em sala" in _texts(ana.page)
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
    assert bia.game_screen is None and "Criar uma sala" in _texts(bia.page)
    assert not lobby.matches and not lobby.rooms
    assert all(owner != "a" for handlers in hub.handlers.values() for owner, _ in handlers)


def test_sound_preference_stays_in_memory(tmp_path: Path) -> None:
    store = SessionStore()
    store.path = tmp_path / "settings.json"
    store.save(Settings(sound=False))
    assert store.load().sound is False and not store.path.exists()


# ------------------------------------------------------------------ servidor sem internet
@pytest.fixture
def client() -> TestClient:
    return TestClient(servidor_sala.create_app("http://192.168.0.10:8000"))


def test_server_serves_emojis_locally(client: TestClient) -> None:
    response = client.get("/assets/fonts/notocoloremoji/v32/qualquer.7.woff2")
    assert response.status_code == 200 and response.headers["content-type"] == "font/woff2"
    assert len(response.content) > 10_000


def test_offline_emoji_font_has_every_emoji_of_the_game() -> None:
    """Emoji novo no jogo? Rode ferramentas/gerar_fonte_emoji.py (senão vira um quadrado na feira)."""

    pytest.importorskip("brotli")
    ttlib = pytest.importorskip("fontTools.ttLib")
    root = Path(servidor_sala.__file__).parent
    used = {
        ch
        for path in [*root.glob("mente_financeira/**/*.py"), *root.glob("mente_financeira/**/*.toml")]
        for ch in path.read_text(encoding="utf-8")
        if ord(ch) >= 0x1F000 or 0x2300 <= ord(ch) < 0x2400
    }
    font = ttlib.TTFont(servidor_sala.EMOJI_FONT).getBestCmap()
    assert sorted(ch for ch in used if ord(ch) not in font) == []


def test_server_draws_qr_codes(client: TestClient) -> None:
    room = client.get("/qr/sala/gato42.png")
    assert room.status_code == 200 and room.headers["content-type"] == "image/png"
    assert client.get("/qr/sala/xx.png").status_code == 404
    assert client.get("/qr/mesa.png").status_code == 200


def test_table_poster_uses_the_network_address(client: TestClient) -> None:
    page = client.get("/mesa", headers={"host": "localhost:8000"})
    assert "http://192.168.0.10:8000" in page.text and "Wi-Fi do estande" in page.text
    phone = client.get("/mesa", headers={"host": "10.0.0.5:8000"})
    assert "http://10.0.0.5:8000" in phone.text


def test_game_page_is_served(client: TestClient) -> None:
    assert client.get("/").status_code == 200
