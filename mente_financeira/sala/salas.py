"""Salas do Duelo em sala (só regras, sem interface).

Quem cria uma sala recebe um código curto, como ``GATO-42``. A outra pessoa
digita o código (ou escaneia o QR code) e as duas começam um Duelo. Tudo fica
na memória do servidor e some quando a pessoa sai: nada é gravado.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from itertools import count
import random
import re
import unicodedata

from mente_financeira.content.memory_deck import MemoryDeck
from mente_financeira.core.memory_game import MemoryGame, Mode

NICKNAME_MIN, NICKNAME_MAX = 2, 16

# Palavras fáceis de ler em voz alta e de digitar no celular (sem acento).
ANIMALS = (
    "GATO", "PATO", "LOBO", "URSO", "SAPO", "TATU", "BODE", "FOCA",
    "PUMA", "MICO", "LULA", "ARARA", "PANDA", "ZEBRA", "COBRA", "TIGRE",
)
CODE_PATTERN = re.compile(r"^([A-Z]+)[\s-]*(\d{2})$")


class NicknameError(ValueError):
    """Apelido vazio, curto ou longo demais."""


class RoomError(ValueError):
    """Código inválido, sala que não existe ou sala que já começou."""


def clean_nickname(raw: str | None) -> str:
    nickname = " ".join((raw or "").split())
    if len(nickname) < NICKNAME_MIN:
        raise NicknameError(f"Digite um apelido com pelo menos {NICKNAME_MIN} letras.")
    if len(nickname) > NICKNAME_MAX:
        raise NicknameError(f"Use no máximo {NICKNAME_MAX} letras no apelido.")
    return nickname


def normalize_code(raw: str | None) -> str:
    """Aceita "gato42", "Gato 42" ou "GATO-42" e devolve "GATO-42"."""

    text = unicodedata.normalize("NFKD", (raw or "").strip().upper())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    found = CODE_PATTERN.match(text)
    if found is None:
        raise RoomError("Código inválido. Ele é assim: GATO-42.")
    return f"{found.group(1)}-{found.group(2)}"


@dataclass(slots=True)
class Player:
    id: str
    nickname: str
    track: str


@dataclass(slots=True)
class Room:
    code: str
    host: Player

    @property
    def track(self) -> str:
        return self.host.track


@dataclass(slots=True)
class Match:
    id: int
    track: str
    players: tuple[Player, Player]
    game: MemoryGame
    left: set[str] = field(default_factory=set)  # quem já saiu da partida

    def seat_of(self, player_id: str) -> int:
        return 0 if self.players[0].id == player_id else 1

    def opponent_of(self, player_id: str) -> Player:
        return self.players[1 - self.seat_of(player_id)]


class Lobby:
    def __init__(
        self,
        tracks: Iterable[str],
        deck_for: Callable[[str], MemoryDeck],
        rng: random.Random | None = None,
    ) -> None:
        self.tracks = tuple(tracks)
        self.deck_for = deck_for
        self.rng = rng or random.Random()
        self.rooms: dict[str, Room] = {}  # código -> sala esperando a segunda pessoa
        self.matches: dict[str, Match] = {}  # id do jogador -> partida
        self._ids = count(1)

    def room_of(self, player_id: str) -> Room | None:
        return next((room for room in self.rooms.values() if room.host.id == player_id), None)

    def create_room(self, player_id: str, nickname: str, track: str) -> Room:
        if track not in self.tracks:
            raise ValueError(f"Trilha sem Duelo em sala: {track}")
        host = Player(player_id, clean_nickname(nickname), track)
        self.leave(player_id)
        code = self._new_code()
        room = self.rooms[code] = Room(code, host)
        return room

    def join(self, player_id: str, nickname: str, code: str) -> Match:
        """Entra na sala do código. Devolve a partida, que começa na hora."""

        nickname = clean_nickname(nickname)
        code = normalize_code(code)
        room = self.rooms.get(code)
        if room is None:
            raise RoomError(f"Não achei a sala {code}. Confira o código com quem criou a sala.")
        if room.host.id == player_id:
            raise RoomError("Esta sala é sua. Passe o código para outra pessoa.")
        self.leave(player_id)
        del self.rooms[code]
        guest = Player(player_id, nickname, room.track)
        game = MemoryGame(self.deck_for(room.track), random.Random(self.rng.random()))
        game.new_game(Mode.DUEL, (room.host.nickname, guest.nickname))
        match = Match(next(self._ids), room.track, (room.host, guest), game)
        self.matches[room.host.id] = self.matches[guest.id] = match
        return match

    def leave(self, player_id: str) -> Match | None:
        """Fecha a sala da pessoa ou tira ela da partida. Devolve a partida que perdeu um jogador."""

        for code, room in list(self.rooms.items()):
            if room.host.id == player_id:
                del self.rooms[code]
        match = self.matches.pop(player_id, None)
        if match is not None:
            match.left.add(player_id)
            match.game.stop()
        return match

    def _new_code(self) -> str:
        while True:
            code = f"{self.rng.choice(ANIMALS)}-{self.rng.randint(10, 99)}"
            if code not in self.rooms:
                return code
