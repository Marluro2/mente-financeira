"""Medalhas: conquistas do jogo da memória, guardadas só no aparelho.

Cada medalha tem uma meta ("Encontre 5 pares seguidos sem errar"). Ao fim de
cada partida, as metas cumpridas viram medalhas novas. Elas ficam nas
preferências do jogo (arquivo local ou armazenamento do navegador), junto do
som e das cores: nada sai do aparelho e nada identifica quem joga.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
from dataclasses import dataclass, replace

from mente_financeira.core.memory_game import MemoryGame, Mode
from mente_financeira.storage import SettingsStore

# Chaves das trilhas (as mesmas de ui/tracks.py).
TRACK_FUNDAMENTAL_1, TRACK_FUNDAMENTAL, TRACK_ENGENHARIA = "fundamental1", "fundamental", "engenharia"
NPV_LABEL = "VPL: VALE A PENA?"  # rótulo do desafio de VPL (core/engineering_challenge.py)

FAST_SOLO_SECONDS = 90  # o relógio corre também durante os desafios
FEW_MISTAKES = 2
COMBO_HOT, COMBO_UNSTOPPABLE = 3, 5
RICH_POINTS = 150
MIN_CHALLENGES = 3  # "acertou todos" só vale com pelo menos 3 desafios


@dataclass(frozen=True, slots=True)
class GameSummary:
    """O que a partida que acabou de terminar deixou (para conferir as metas)."""

    track: str
    mode: Mode
    pairs: int
    moves: int
    stars: int  # Solo: 1 a 3 (no Duelo, 0)
    mistakes: int
    elapsed: int
    best_streak: int
    points: tuple[int, ...]
    challenges: tuple[tuple[int, int], ...]  # (certos, respondidos) por jogador
    right_labels: frozenset[str] = frozenset()  # tipos de desafio acertados

    @classmethod
    def of(cls, game: MemoryGame, track: str, right_labels: Collection[str] = ()) -> GameSummary:
        players = len(game.players)
        return cls(
            track=track,
            mode=game.mode,
            pairs=game.pairs,
            moves=game.moves,
            stars=game.stars if game.mode is Mode.SOLO else 0,
            mistakes=game.mistakes,
            elapsed=game.elapsed,
            best_streak=game.best_streak,
            points=tuple(game.points[:players]),
            challenges=tuple((right, total) for right, total in game.challenge_stats[:players]),
            right_labels=frozenset(right_labels),
        )

    @property
    def solo(self) -> bool:
        return self.mode is Mode.SOLO


@dataclass(frozen=True, slots=True)
class Medal:
    key: str
    emoji: str
    title: str
    goal: str  # meta, escrita como convite ("Termine...")
    check: Callable[[GameSummary, frozenset[str]], bool]  # (partida, medalhas que já tinha + novas)


def _all_right(summary: GameSummary) -> bool:
    return any(total >= MIN_CHALLENGES and right == total for right, total in summary.challenges)


TRACK_MEDALS = {
    TRACK_FUNDAMENTAL_1: "trilha_fundamental1",
    TRACK_FUNDAMENTAL: "trilha_fundamental",
    TRACK_ENGENHARIA: "trilha_engenharia",
}

MEDALS: tuple[Medal, ...] = (
    Medal("primeira_partida", "🎯", "Primeira partida", "Termine uma partida.", lambda g, _: True),
    Medal("tres_estrelas", "🌟", "Três estrelas", "Ganhe 3 estrelas no Solo.", lambda g, _: g.stars == 3),
    Medal(
        "memoria_elefante",
        "🐘",
        "Memória de elefante",
        f"Termine o Solo errando no máximo {FEW_MISTAKES} pares.",
        lambda g, _: g.solo and g.mistakes <= FEW_MISTAKES,
    ),
    Medal(
        "foguete",
        "🚀",
        "Foguete",
        f"Termine o Solo em até {FAST_SOLO_SECONDS} segundos.",
        lambda g, _: g.solo and g.elapsed <= FAST_SOLO_SECONDS,
    ),
    Medal(
        "pegando_fogo",
        "🔥",
        "Pegando fogo",
        f"Encontre {COMBO_HOT} pares seguidos sem errar.",
        lambda g, _: g.best_streak >= COMBO_HOT,
    ),
    Medal(
        "imparavel",
        "💥",
        "Imparável",
        f"Encontre {COMBO_UNSTOPPABLE} pares seguidos sem errar.",
        lambda g, _: g.best_streak >= COMBO_UNSTOPPABLE,
    ),
    Medal(
        "genio_calculos",
        "🧠",
        "Gênio dos cálculos",
        "Acerte todos os Desafios Relâmpago de uma partida.",
        lambda g, _: _all_right(g),
    ),
    Medal(
        "cofrinho_cheio",
        "💰",
        "Cofrinho cheio",
        f"Faça {RICH_POINTS} pontos numa partida.",
        lambda g, _: max(g.points, default=0) >= RICH_POINTS,
    ),
    Medal("duelo", "🤝", "Duelo de cérebros", "Termine um Duelo com alguém.", lambda g, _: g.mode is Mode.DUEL),
    Medal(
        "primeiro_vpl",
        "🏭",
        "Primeiro VPL",
        "Acerte um desafio de VPL na Engenharia de Produção.",
        lambda g, _: NPV_LABEL in g.right_labels,
    ),
    Medal(
        TRACK_MEDALS[TRACK_FUNDAMENTAL_1],
        "🐷",
        "Primeiras economias",
        "Termine uma partida do Ensino Fundamental 1.",
        lambda g, _: g.track == TRACK_FUNDAMENTAL_1,
    ),
    Medal(
        TRACK_MEDALS[TRACK_FUNDAMENTAL],
        "🎒",
        "Craque da porcentagem",
        "Termine uma partida do Ensino Fundamental 2.",
        lambda g, _: g.track == TRACK_FUNDAMENTAL,
    ),
    Medal(
        TRACK_MEDALS[TRACK_ENGENHARIA],
        "📈",
        "Engenharia em ação",
        "Termine uma partida da Engenharia de Produção.",
        lambda g, _: g.track == TRACK_ENGENHARIA,
    ),
    Medal(
        "todas_trilhas",
        "🌎",
        "Volta ao mundo",
        "Termine uma partida em cada uma das 3 trilhas.",
        lambda g, owned: set(TRACK_MEDALS.values()) <= owned,
    ),
)

BY_KEY = {medal.key: medal for medal in MEDALS}


def new_medals(summary: GameSummary, owned: Collection[str]) -> list[Medal]:
    """Medalhas que a partida acabou de dar (as que já tinha não contam de novo)."""

    have = set(owned)
    won: list[Medal] = []
    for medal in MEDALS:  # em ordem: "Volta ao mundo" já vê as medalhas de trilha desta partida
        if medal.key not in have and medal.check(summary, frozenset(have)):
            have.add(medal.key)
            won.append(medal)
    return won


class MedalBook:
    """Medalhas deste aparelho, guardadas nas preferências do jogo."""

    def __init__(self, store: SettingsStore) -> None:
        self.store = store

    def owned(self) -> list[Medal]:
        keys = set(self.store.load().medals)
        return [medal for medal in MEDALS if medal.key in keys]

    def record(self, summary: GameSummary) -> list[Medal]:
        """Confere as metas da partida e guarda as medalhas novas."""

        settings = self.store.load()
        won = new_medals(summary, settings.medals)
        if won:
            self.store.save(replace(settings, medals=[*settings.medals, *(m.key for m in won)]))
        return won
