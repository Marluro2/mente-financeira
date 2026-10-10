"""Ranking da feira: os melhores apelidos do dia no cartaz do estande.

Dois placares: o do Duelo em sala (pontos da partida) e o do Quiz ao vivo.
Cada apelido aparece uma vez por placar, com o melhor resultado. Fica só na
memória do notebook e some quando o servidor fecha: nada é gravado. Quem
cuida do estande pode tirar um apelido ou limpar tudo pelo cartaz.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import threading

DUEL, QUIZ = "duelo", "quiz"
BOARDS = (DUEL, QUIZ)
TOP = 10


@dataclass(slots=True)
class Entry:
    nickname: str
    points: int
    detail: str  # trilha da partida ("Ensino Fundamental 2")


class FairRanking:
    def __init__(self) -> None:
        self.lock = threading.Lock()  # várias sessões terminam partidas ao mesmo tempo
        self.boards: dict[str, dict[str, Entry]] = {board: {} for board in BOARDS}
        self.recorded: set[tuple[str, int]] = set()  # partidas e rodadas já somadas

    def record(self, board: str, game_id: int, results: Iterable[tuple[str, int]], detail: str) -> bool:
        """Soma o resultado de uma partida (ou rodada do quiz). Só a primeira chamada vale."""

        with self.lock:
            if (board, game_id) in self.recorded:
                return False
            self.recorded.add((board, game_id))
            entries = self.boards[board]
            for nickname, points in results:
                if points <= 0:
                    continue  # quem não pontuou não entra no placar
                key = nickname.casefold()
                best = entries.get(key)
                if best is None or points > best.points:
                    entries[key] = Entry(nickname, points, detail)
            return True

    def top(self, board: str, limit: int = TOP) -> list[Entry]:
        with self.lock:
            entries = list(self.boards[board].values())
        return sorted(entries, key=lambda e: (-e.points, e.nickname.casefold()))[:limit]

    def remove(self, board: str, nickname: str) -> bool:
        """Tira um apelido do placar (ex.: apelido ofensivo)."""

        with self.lock:
            return self.boards.get(board, {}).pop(nickname.casefold(), None) is not None

    def clear(self) -> None:
        with self.lock:
            for entries in self.boards.values():
                entries.clear()

    def as_dict(self) -> dict[str, list[dict[str, object]]]:
        return {
            board: [{"nickname": e.nickname, "points": e.points, "detail": e.detail} for e in self.top(board)]
            for board in BOARDS
        }
