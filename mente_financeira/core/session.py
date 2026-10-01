"""Motor do jogo: regras da partida, independentes da interface.

A interface apenas chama os métodos desta classe e redesenha a tela conforme o
estado resultante. Assim, as regras (vez, pontuação, erros, cronômetro,
progressão) podem ser verificadas por testes automatizados sem abrir janelas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import random

from mente_financeira.content import MemoryPair, Phase, Track

DEFAULT_PLAYERS = ("Jogador 1 🐯", "Jogador 2 🐼")
MAX_NAME_LENGTH = 24
TIMER_SECONDS = 90

QUESTION = "question"
RESOLUTION = "resolution"


class Selection(Enum):
    """Resultado de tocar em uma carta."""

    OPENED = auto()  # a carta foi aberta; aguardando a próxima
    READY = auto()  # questão e resolução abertas; chamar ``resolve()``
    NEED_QUESTION = auto()  # tocou numa resolução antes de abrir uma questão
    NEED_RESOLUTION = auto()  # já há uma questão aberta
    IGNORED = auto()  # carta já encontrada, tabuleiro bloqueado etc.


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    matched: bool
    pair: MemoryPair | None = None


@dataclass(frozen=True, slots=True)
class PhaseSummary:
    stars: int
    message: str
    mistakes: int
    time_left: int


def clean_name(raw: str | None, fallback: str) -> str:
    return " ".join((raw or "").split())[:MAX_NAME_LENGTH] or fallback


class GameSession:
    def __init__(self, track: Track, rng: random.Random | None = None, timer_seconds: int = TIMER_SECONDS) -> None:
        self.track = track
        self.rng = rng or random.Random()
        self.timer_seconds = timer_seconds
        self.players = list(DEFAULT_PLAYERS)
        self.scores = [0, 0]
        self.phase_start_scores = [0, 0]
        self.turn = 0
        self.phase_index = 0
        self.total_mistakes = 0

        self.pairs: list[MemoryPair] = []
        self.pairs_by_id: dict[str, MemoryPair] = {}
        self.question_order: list[str] = []
        self.resolution_order: list[str] = []
        self.selected_question: str | None = None
        self.selected_resolution: str | None = None
        self.matched: set[str] = set()
        self.locked = False
        self.phase_active = False
        self.timer_paused = False
        self.time_left = timer_seconds
        self.phase_mistakes = 0
        self.advance_available = False

    # ------------------------------------------------------------------ dados
    @property
    def phase(self) -> Phase:
        return self.track.phases[self.phase_index]

    @property
    def phase_count(self) -> int:
        return len(self.track.phases)

    @property
    def is_last_phase(self) -> bool:
        return self.phase_index == self.phase_count - 1

    @property
    def current_player(self) -> str:
        return self.players[self.turn]

    @property
    def is_phase_complete(self) -> bool:
        return bool(self.pairs) and len(self.matched) == len(self.pairs)

    @property
    def overall_progress(self) -> float:
        completed = len(self.matched) / max(1, len(self.pairs))
        return (self.phase_index + completed) / self.phase_count

    def order(self, side: str) -> list[str]:
        return self.question_order if side == QUESTION else self.resolution_order

    def selected(self, side: str) -> str | None:
        return self.selected_question if side == QUESTION else self.selected_resolution

    # ------------------------------------------------------------- partida
    def set_players(self, first: str | None, second: str | None) -> None:
        self.players = [clean_name(first, DEFAULT_PLAYERS[0]), clean_name(second, DEFAULT_PLAYERS[1])]

    def new_game(self) -> None:
        self.scores = [0, 0]
        self.phase_start_scores = [0, 0]
        self.turn = 0
        self.phase_index = 0
        self.total_mistakes = 0
        self.start_phase(repeat=False)

    def start_phase(self, *, repeat: bool) -> None:
        """Sorteia uma nova fase. Ao repetir, desfaz os pontos da tentativa."""

        if repeat:
            self.scores = self.phase_start_scores.copy()
        else:
            self.phase_start_scores = self.scores.copy()

        self.pairs = self.track.build_phase(self.phase_index, self.rng)
        self.pairs_by_id = {pair.pair_id: pair for pair in self.pairs}
        self.question_order = [pair.pair_id for pair in self.pairs]
        self.resolution_order = [pair.pair_id for pair in self.pairs]
        self.rng.shuffle(self.question_order)
        self.rng.shuffle(self.resolution_order)
        self.selected_question = None
        self.selected_resolution = None
        self.matched.clear()
        self.locked = False
        self.phase_active = True
        self.timer_paused = False
        self.time_left = self.timer_seconds
        self.phase_mistakes = 0
        self.advance_available = False

    def stop(self) -> None:
        self.phase_active = False

    def select(self, side: str, pair_id: str) -> Selection:
        if self.locked or not self.phase_active or pair_id in self.matched:
            return Selection.IGNORED
        if side == QUESTION:
            if self.selected_question is not None:
                return Selection.NEED_RESOLUTION
            self.selected_question = pair_id
            return Selection.OPENED
        if self.selected_question is None:
            return Selection.NEED_QUESTION
        if self.selected_resolution is not None:
            return Selection.IGNORED
        self.selected_resolution = pair_id
        self.locked = True
        return Selection.READY

    def resolve(self) -> MatchOutcome:
        """Compara as duas cartas abertas. Acerto: ponto e o jogador continua."""

        question_id, resolution_id = self.selected_question, self.selected_resolution
        if question_id is None or resolution_id is None:
            raise RuntimeError("resolve() exige uma questão e uma resolução abertas.")
        self.selected_question = None
        self.selected_resolution = None
        self.locked = False
        if question_id == resolution_id:
            self.matched.add(question_id)
            self.scores[self.turn] += 1
            self.timer_paused = True  # pausa durante a leitura da explicação
            return MatchOutcome(True, self.pairs_by_id[question_id])
        self.phase_mistakes += 1
        self.total_mistakes += 1
        self.turn = 1 - self.turn
        return MatchOutcome(False)

    def resume_timer(self) -> None:
        self.timer_paused = False

    def tick(self) -> bool:
        """Avança o cronômetro um segundo. Devolve ``True`` se o tempo acabou."""

        if not self.phase_active or self.timer_paused:
            return False
        self.time_left = max(0, self.time_left - 1)
        if self.time_left == 0:
            self.phase_active = False
            self.locked = True
            return True
        return False

    def finish_phase(self) -> PhaseSummary:
        self.phase_active = False
        self.timer_paused = False
        self.locked = True
        self.advance_available = True
        ratio = self.time_left / self.timer_seconds
        if ratio >= 0.60 and self.phase_mistakes <= 1:
            stars, message = 3, "Excelente memória e ótimo raciocínio!"
        elif ratio >= 0.30 or self.phase_mistakes <= 3:
            stars, message = 2, "Muito bem! Você dominou esta etapa."
        else:
            stars, message = 1, "Fase concluída — cada tentativa também ensina."
        return PhaseSummary(stars, message, self.phase_mistakes, self.time_left)

    def advance(self) -> bool:
        """Vai para a próxima fase. Devolve ``False`` se não houver mais fases."""

        if not self.advance_available or self.is_last_phase:
            return False
        self.phase_index += 1
        self.start_phase(repeat=False)
        return True

    def final_result(self) -> str:
        first, second = self.scores
        if first > second:
            return f"{self.players[0]} venceu!"
        if second > first:
            return f"{self.players[1]} venceu!"
        return "A partida terminou empatada!"
