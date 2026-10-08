"""Sala de espera do modo online (só regras, sem interface).

Cada pessoa conectada ao servidor tem um ``id`` de sessão. Ao escolher a
trilha e o apelido, ela entra na fila daquela trilha; quando chega a segunda
pessoa da mesma trilha, as duas formam uma partida (Duelo). Tudo fica na
memória do servidor e some quando a pessoa sai: nada é gravado.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from itertools import count
import random

from mente_financeira.content.memory_deck import MemoryDeck
from mente_financeira.core.memory_game import MemoryGame, Mode

NICKNAME_MIN, NICKNAME_MAX = 2, 16


class NicknameError(ValueError):
    """Apelido vazio, curto ou longo demais."""


def clean_nickname(raw: str | None) -> str:
    nickname = " ".join((raw or "").split())
    if len(nickname) < NICKNAME_MIN:
        raise NicknameError(f"Digite um apelido com pelo menos {NICKNAME_MIN} letras.")
    if len(nickname) > NICKNAME_MAX:
        raise NicknameError(f"Use no máximo {NICKNAME_MAX} letras no apelido.")
    return nickname


@dataclass(slots=True)
class Player:
    id: str
    nickname: str
    track: str


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
        self.waiting: dict[str, Player] = {}  # trilha -> quem está esperando
        self.matches: dict[str, Match] = {}  # id do jogador -> partida
        self.browsing: dict[str, str] = {}  # id -> trilha escolhida, ainda na sala
        self._ids = count(1)

    # ------------------------------------------------------------ consultas
    def counts(self) -> dict[str, int]:
        """Quantas pessoas estão no modo online em cada trilha."""

        totals = dict.fromkeys(self.tracks, 0)
        for track in self.browsing.values():
            totals[track] += 1
        for player in self.waiting.values():
            totals[player.track] += 1
        for player_id, match in self.matches.items():
            if player_id not in match.left:
                totals[match.track] += 1
        return totals

    def is_waiting(self, player_id: str) -> bool:
        return any(p.id == player_id for p in self.waiting.values())

    # ------------------------------------------------------------ ações
    def browse(self, player_id: str, track: str) -> None:
        """Pessoa na sala, com a trilha escolhida, ainda sem procurar partida."""

        self._check_track(track)
        self.leave(player_id)
        self.browsing[player_id] = track

    def wait(self, player_id: str, nickname: str, track: str) -> Match | None:
        """Entra na fila da trilha. Devolve a partida se já havia alguém esperando."""

        self._check_track(track)
        player = Player(player_id, clean_nickname(nickname), track)
        self.leave(player_id)
        opponent = self.waiting.pop(track, None)
        if opponent is None:
            self.waiting[track] = player
            return None
        game = MemoryGame(self.deck_for(track), random.Random(self.rng.random()))
        game.new_game(Mode.DUEL, (opponent.nickname, player.nickname))
        match = Match(next(self._ids), track, (opponent, player), game)
        self.matches[opponent.id] = self.matches[player.id] = match
        return match

    def leave(self, player_id: str) -> Match | None:
        """Sai da sala, da fila ou da partida. Devolve a partida que perdeu um jogador."""

        self.browsing.pop(player_id, None)
        for track, player in list(self.waiting.items()):
            if player.id == player_id:
                del self.waiting[track]
        match = self.matches.pop(player_id, None)
        if match is not None:
            match.left.add(player_id)
            match.game.stop()
        return match

    def _check_track(self, track: str) -> None:
        if track not in self.tracks:
            raise ValueError(f"Trilha sem modo online: {track}")
