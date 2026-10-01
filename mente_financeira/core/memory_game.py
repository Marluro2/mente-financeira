"""Motor do jogo da memória tradicional (Nível 1).

Cartas iguais formam pares. No modo Solo o objetivo é terminar com poucas
jogadas. No Duelo, quem forma um par marca ponto e enfrenta um Desafio
Relâmpago de porcentagem: acertando, continua jogando; errando, passa a vez.
Quem erra o par também passa a vez.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, StrEnum, auto
import random

from mente_financeira.content.memory_deck import Concept, MemoryDeck
from mente_financeira.core.session import DEFAULT_PLAYERS, clean_name


class Mode(StrEnum):
    SOLO = "solo"
    DUEL = "duelo"


class Flip(Enum):
    OPENED = auto()  # primeira carta virada
    READY = auto()  # segunda carta virada; chamar ``resolve()``
    IGNORED = auto()  # carta já aberta, já encontrada ou tabuleiro bloqueado


@dataclass(frozen=True, slots=True)
class Outcome:
    matched: bool
    concept: Concept
    challenge: bool = False  # Duelo: o jogador precisa responder o desafio


class MemoryGame:
    def __init__(self, deck: MemoryDeck, rng: random.Random | None = None) -> None:
        self.deck = deck
        self.rng = rng or random.Random()
        self.mode = Mode.SOLO
        self.players = [DEFAULT_PLAYERS[0]]
        self.cards: list[Concept] = []
        self.face_up: list[int] = []
        self.matched: set[int] = set()
        self.learned: list[Concept] = []
        self.moves = 0
        self.mistakes = 0
        self.scores = [0, 0]
        self.turn = 0
        self.elapsed = 0
        self.active = False
        self.awaiting_challenge = False
        # [acertos, tentativas] do Desafio Relâmpago, por jogador
        self.challenge_stats = [[0, 0], [0, 0]]

    # ------------------------------------------------------------ partida
    def new_game(self, mode: Mode = Mode.SOLO, names: tuple[str | None, str | None] = (None, None)) -> None:
        self.mode = mode
        if mode is Mode.SOLO:
            self.players = [clean_name(names[0], "Você")]
        else:
            self.players = [clean_name(names[0], DEFAULT_PLAYERS[0]), clean_name(names[1], DEFAULT_PLAYERS[1])]
        chosen = self.rng.sample(self.deck.concepts, k=self.deck.pairs)
        self.cards = chosen * 2
        self.rng.shuffle(self.cards)
        self.face_up = []
        self.matched = set()
        self.learned = []
        self.moves = 0
        self.mistakes = 0
        self.scores = [0, 0]
        self.turn = 0
        self.elapsed = 0
        self.active = True
        self.awaiting_challenge = False
        self.challenge_stats = [[0, 0], [0, 0]]

    def restart(self) -> None:
        """Nova partida com o mesmo modo e os mesmos jogadores."""

        self.new_game(self.mode, (self.players[0], self.players[1] if len(self.players) > 1 else None))

    # -------------------------------------------------------------- dados
    @property
    def pairs(self) -> int:
        return self.deck.pairs

    @property
    def found_pairs(self) -> int:
        return len(self.matched) // 2

    @property
    def is_complete(self) -> bool:
        return bool(self.cards) and len(self.matched) == len(self.cards)

    @property
    def locked(self) -> bool:
        return len(self.face_up) == 2

    @property
    def current_player(self) -> str:
        return self.players[self.turn]

    def is_revealed(self, index: int) -> bool:
        return index in self.matched or index in self.face_up

    # -------------------------------------------------------------- regras
    def flip(self, index: int) -> Flip:
        if (
            not self.active
            or self.locked
            or self.awaiting_challenge
            or self.is_revealed(index)
            or not 0 <= index < len(self.cards)
        ):
            return Flip.IGNORED
        self.face_up.append(index)
        return Flip.READY if self.locked else Flip.OPENED

    def resolve(self) -> Outcome:
        if not self.locked:
            raise RuntimeError("resolve() exige duas cartas viradas.")
        first, second = self.face_up
        self.face_up = []
        self.moves += 1
        concept = self.cards[first]
        if concept.id == self.cards[second].id:
            self.matched.update((first, second))
            self.learned.append(concept)
            self.scores[self.turn] += 1
            if self.is_complete:
                self.active = False  # último par: o jogo acaba, sem desafio
            elif self.mode is Mode.DUEL:
                self.awaiting_challenge = True
            return Outcome(True, concept, challenge=self.awaiting_challenge)
        self.mistakes += 1
        if self.mode is Mode.DUEL:
            self.turn = 1 - self.turn
        return Outcome(False, concept)

    def answer_challenge(self, correct: bool) -> None:
        """Acerto: o jogador continua. Erro: a vez passa ao adversário.

        O ponto do par já encontrado é mantido em ambos os casos.
        """

        if not self.awaiting_challenge:
            raise RuntimeError("Não há desafio aguardando resposta.")
        stats = self.challenge_stats[self.turn]
        stats[1] += 1
        if correct:
            stats[0] += 1
        else:
            self.turn = 1 - self.turn
        self.awaiting_challenge = False

    def tick(self) -> None:
        if self.active:
            self.elapsed += 1

    def stop(self) -> None:
        self.active = False

    # ----------------------------------------------------------- resultado
    @property
    def stars(self) -> int:
        """Solo: 3 estrelas com até 12 jogadas, 2 com até 16, senão 1.

        O mínimo possível é ``pairs`` jogadas (8), acertando tudo de primeira.
        """

        if self.moves <= self.pairs + 4:
            return 3
        if self.moves <= self.pairs * 2:
            return 2
        return 1

    def winner_text(self) -> str:
        if self.mode is Mode.SOLO:
            return f"{self.players[0]} encontrou os {self.pairs} pares!"
        first, second = self.scores
        if first > second:
            return f"{self.players[0]} venceu o duelo!"
        if second > first:
            return f"{self.players[1]} venceu o duelo!"
        return "Empate! Os dois mandaram bem."
