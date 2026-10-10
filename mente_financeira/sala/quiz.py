"""Quiz ao vivo da feira (só regras, sem interface).

O notebook mostra as perguntas na tela grande e cada pessoa responde pelo
celular, como num show de perguntas: quem acerta mais rápido ganha mais
pontos. As perguntas vêm do Desafio Relâmpago da trilha escolhida. Só pedimos
um apelido, e tudo fica na memória: nada é gravado.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
import math
import random
import threading
import time

from mente_financeira.core.percent_challenge import Challenge, ChallengeKit
from mente_financeira.sala.salas import NicknameError, clean_nickname

QUESTION_COUNT = 8
QUESTION_SECONDS = 30
CORRECT_POINTS = 100  # por acertar
SPEED_POINTS = 100  # bônus máximo, para quem responde na hora
PLAYERS_MAX = 60


class Phase(Enum):
    LOBBY = "lobby"  # esperando gente entrar
    QUESTION = "question"  # pergunta aberta, relógio correndo
    REVEAL = "reveal"  # resposta certa e placar parcial
    FINISHED = "finished"  # pódio


class QuizError(ValueError):
    """Ação fora de hora (ex.: começar sem ninguém) ou quiz lotado."""


@dataclass(slots=True)
class QuizPlayer:
    id: str
    nickname: str
    score: int = 0
    choice: int | None = None  # alternativa marcada na pergunta atual
    gain: int = 0  # pontos da pergunta atual (somados na revelação)
    correct: int = 0  # acertos no quiz
    streak: int = 0  # acertos seguidos

    def clear_answer(self) -> None:
        self.choice, self.gain = None, 0


def draw_questions(kit: ChallengeKit, count: int, rng: random.Random) -> list[Challenge]:
    """Sorteia ``count`` perguntas sem repetir enunciado."""

    questions: list[Challenge] = []
    seen: set[str] = set()
    for _ in range(count * 30):
        challenge = kit.make(rng)
        if challenge.question not in seen:
            seen.add(challenge.question)
            questions.append(challenge)
            if len(questions) == count:
                break
    return questions


class Quiz:
    """Um quiz por servidor, compartilhado pelo notebook e por todos os celulares."""

    def __init__(
        self,
        kits: Mapping[str, ChallengeKit],
        track: str,
        *,
        count: int = QUESTION_COUNT,
        seconds: int = QUESTION_SECONDS,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.kits = dict(kits)
        self.track = track
        self.count = count
        self.seconds = seconds
        self.rng = rng or random.Random()
        self.clock = clock
        self.lock = threading.RLock()  # várias sessões mexem no mesmo quiz
        self.phase = Phase.LOBBY
        self.players: dict[str, QuizPlayer] = {}
        self.questions: list[Challenge] = []
        self.index = -1
        self.deadline = 0.0
        self.round = 0  # quantas rodadas já começaram (para o ranking não somar duas vezes)

    # ------------------------------------------------------------ consulta
    @property
    def question(self) -> Challenge | None:
        if self.phase in (Phase.QUESTION, Phase.REVEAL):
            return self.questions[self.index]
        return None

    @property
    def number(self) -> int:
        """Número da pergunta atual (começa em 1)."""

        return self.index + 1

    @property
    def total(self) -> int:
        return len(self.questions) or self.count

    @property
    def is_last(self) -> bool:
        return self.number >= len(self.questions)

    def remaining(self) -> int:
        """Segundos que faltam na pergunta aberta (arredondado para cima)."""

        if self.phase is not Phase.QUESTION:
            return 0
        return max(0, math.ceil(self.deadline - self.clock()))

    @property
    def time_up(self) -> bool:
        return self.phase is Phase.QUESTION and self.clock() >= self.deadline

    @property
    def answered(self) -> int:
        return sum(player.choice is not None for player in self.players.values())

    @property
    def all_answered(self) -> bool:
        return bool(self.players) and self.answered == len(self.players)

    def distribution(self) -> list[int]:
        """Quantas pessoas marcaram cada alternativa."""

        question = self.question
        counts = [0] * (len(question.options) if question else 0)
        for player in self.players.values():
            if player.choice is not None and player.choice < len(counts):
                counts[player.choice] += 1
        return counts

    def ranking(self) -> list[QuizPlayer]:
        return sorted(self.players.values(), key=lambda p: (-p.score, p.nickname.casefold()))

    def place_of(self, player_id: str) -> int:
        """Colocação (empate divide a posição: 1º, 1º, 3º)."""

        player = self.players[player_id]
        return 1 + sum(other.score > player.score for other in self.players.values())

    # ------------------------------------------------------------ jogadores
    def join(self, player_id: str, nickname: str | None) -> QuizPlayer:
        name = clean_nickname(nickname)
        with self.lock:
            taken = any(p.nickname.casefold() == name.casefold() for p in self.players.values() if p.id != player_id)
            if taken:
                raise NicknameError("Esse apelido já está no quiz. Escolha outro.")
            if player_id in self.players:
                self.players[player_id].nickname = name
            elif len(self.players) >= PLAYERS_MAX:
                raise QuizError("O quiz está lotado. Espere a próxima rodada.")
            else:
                self.players[player_id] = QuizPlayer(player_id, name)
            return self.players[player_id]

    def leave(self, player_id: str) -> QuizPlayer | None:
        with self.lock:
            return self.players.pop(player_id, None)

    # ------------------------------------------------------------ rodada
    def choose_track(self, track: str) -> None:
        with self.lock:
            if track not in self.kits:
                raise QuizError("Trilha sem perguntas.")
            if self.phase is Phase.LOBBY:
                self.track = track

    def start(self) -> None:
        with self.lock:
            if self.phase is not Phase.LOBBY:
                raise QuizError("O quiz já começou.")
            if not self.players:
                raise QuizError("Espere pelo menos uma pessoa entrar.")
            self.questions = draw_questions(self.kits[self.track], self.count, self.rng)
            self.round += 1
            for player in self.players.values():
                player.score = player.correct = player.streak = 0
                player.clear_answer()
            self.index = -1
            self._open_next()

    def _open_next(self) -> None:
        self.index += 1
        for player in self.players.values():
            player.clear_answer()
        self.phase = Phase.QUESTION
        self.deadline = self.clock() + self.seconds

    def answer(self, player_id: str, choice: int) -> bool:
        """Registra a resposta (uma por pergunta, dentro do tempo)."""

        with self.lock:
            player = self.players.get(player_id)
            question = self.question
            if player is None or question is None or self.phase is not Phase.QUESTION or self.time_up:
                return False
            if player.choice is not None or not 0 <= choice < len(question.options):
                return False
            player.choice = choice
            if question.is_correct(choice):
                left = max(0.0, self.deadline - self.clock()) / self.seconds
                player.gain = CORRECT_POINTS + round(SPEED_POINTS * left)
            return True

    def reveal(self, number: int) -> bool:
        """Fecha a pergunta ``number`` e soma os pontos. Só a primeira chamada vale."""

        with self.lock:
            if self.phase is not Phase.QUESTION or number != self.number:
                return False
            question = self.questions[self.index]
            for player in self.players.values():
                if player.choice is not None and question.is_correct(player.choice):
                    player.score += player.gain
                    player.correct += 1
                    player.streak += 1
                else:
                    player.streak = 0
            self.phase = Phase.REVEAL
            return True

    def advance(self, number: int) -> bool:
        """Depois da revelação da pergunta ``number``: próxima pergunta ou pódio."""

        with self.lock:
            if self.phase is not Phase.REVEAL or number != self.number:
                return False
            if self.is_last:
                self.phase = Phase.FINISHED
            else:
                self._open_next()
            return True

    def restart(self) -> None:
        """Volta para a sala de espera, com as mesmas pessoas e placar zerado."""

        with self.lock:
            self.phase = Phase.LOBBY
            self.questions = []
            self.index = -1
            for player in self.players.values():
                player.score = player.correct = player.streak = 0
                player.clear_answer()
