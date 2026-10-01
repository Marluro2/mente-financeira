from collections import Counter
import random

import pytest

from mente_financeira.content.memory_deck import load_memory_deck
from mente_financeira.core.memory_game import Flip, MemoryGame, Mode

DECK = load_memory_deck()


def _game(mode: Mode = Mode.SOLO, seed: int = 1) -> MemoryGame:
    game = MemoryGame(DECK, random.Random(seed))
    game.new_game(mode, ("Ana", "Bruno"))
    return game


def _pair_of(game: MemoryGame, index: int) -> int:
    return next(i for i, c in enumerate(game.cards) if i != index and c.id == game.cards[index].id)


def _wrong_of(game: MemoryGame, index: int) -> int:
    return next(i for i, c in enumerate(game.cards) if c.id != game.cards[index].id and not game.is_revealed(i))


def test_sixteen_cards_in_eight_pairs() -> None:
    game = _game()
    assert len(game.cards) == 16
    assert set(Counter(c.id for c in game.cards).values()) == {2}


def test_games_vary_between_rounds() -> None:
    game = _game(seed=5)
    rounds = set()
    for _ in range(6):
        game.restart()
        rounds.add(frozenset(c.id for c in game.cards))
    assert len(rounds) > 1


def test_match_keeps_cards_open() -> None:
    game = _game()
    other = _pair_of(game, 0)
    assert game.flip(0) is Flip.OPENED
    assert game.flip(0) is Flip.IGNORED  # a mesma carta
    assert game.flip(other) is Flip.READY
    assert game.flip(_wrong_of(game, 0)) is Flip.IGNORED  # bloqueado com 2 abertas
    outcome = game.resolve()
    assert outcome.matched and outcome.concept is game.cards[0]
    assert {0, other} <= game.matched
    assert game.learned == [game.cards[0]]
    assert game.moves == 1 and game.mistakes == 0


def test_mismatch_hides_cards_again() -> None:
    game = _game()
    wrong = _wrong_of(game, 0)
    game.flip(0)
    game.flip(wrong)
    assert not game.resolve().matched
    assert not game.is_revealed(0) and not game.is_revealed(wrong)
    assert game.moves == 1 and game.mistakes == 1
    assert game.turn == 0  # no Solo não há troca de vez


def test_duel_passes_turn_on_mistake_and_keeps_it_on_match() -> None:
    game = _game(Mode.DUEL)
    assert game.players == ["Ana", "Bruno"]
    game.flip(0)
    game.flip(_wrong_of(game, 0))
    game.resolve()
    assert game.current_player == "Bruno"
    game.flip(0)
    game.flip(_pair_of(game, 0))
    game.resolve()
    assert game.scores == [0, 1] and game.current_player == "Bruno"


def test_duel_match_requires_a_challenge_answer() -> None:
    game = _game(Mode.DUEL)
    game.flip(0)
    game.flip(_pair_of(game, 0))
    outcome = game.resolve()
    assert outcome.challenge and game.awaiting_challenge
    assert game.flip(_wrong_of(game, 0)) is Flip.IGNORED  # tabuleiro travado

    game.answer_challenge(True)
    assert game.current_player == "Ana" and not game.awaiting_challenge
    assert game.challenge_stats == [[1, 1], [0, 0]]
    assert game.flip(_wrong_of(game, 0)) is Flip.OPENED  # tabuleiro liberado


def test_wrong_challenge_passes_turn_but_keeps_the_point() -> None:
    game = _game(Mode.DUEL)
    game.flip(0)
    game.flip(_pair_of(game, 0))
    game.resolve()
    game.answer_challenge(False)
    assert game.scores == [1, 0]
    assert game.current_player == "Bruno"
    assert game.challenge_stats == [[0, 1], [0, 0]]
    with pytest.raises(RuntimeError):
        game.answer_challenge(True)


def test_solo_has_no_challenge() -> None:
    game = _game(Mode.SOLO)
    game.flip(0)
    game.flip(_pair_of(game, 0))
    assert not game.resolve().challenge
    assert not game.awaiting_challenge


def test_last_pair_ends_the_duel_without_challenge() -> None:
    game = _game(Mode.DUEL)
    for index in range(16):
        if not game.is_revealed(index):
            game.flip(index)
            game.flip(_pair_of(game, index))
            outcome = game.resolve()
            if game.awaiting_challenge:
                game.answer_challenge(True)
    assert game.is_complete
    assert not outcome.challenge and not game.awaiting_challenge
    assert game.challenge_stats[0] == [7, 7]


def _solve(game: MemoryGame) -> None:
    for index in range(len(game.cards)):
        if not game.is_revealed(index):
            game.flip(index)
            game.flip(_pair_of(game, index))
            game.resolve()


def test_perfect_game_gives_three_stars() -> None:
    game = _game()
    _solve(game)
    assert game.is_complete and not game.active
    assert game.moves == 8 and game.stars == 3
    assert len(game.learned) == 8
    assert game.flip(0) is Flip.IGNORED


@pytest.mark.parametrize(("moves", "stars"), [(8, 3), (12, 3), (13, 2), (16, 2), (17, 1)])
def test_star_thresholds(moves: int, stars: int) -> None:
    game = _game()
    game.moves = moves
    assert game.stars == stars


def test_clock_only_runs_while_playing() -> None:
    game = _game()
    game.tick()
    game.tick()
    assert game.elapsed == 2
    game.stop()
    game.tick()
    assert game.elapsed == 2


def test_winner_texts() -> None:
    game = _game(Mode.DUEL)
    game.scores = [5, 3]
    assert game.winner_text() == "Ana venceu o duelo!"
    game.scores = [4, 4]
    assert "Empate" in game.winner_text()
    solo = MemoryGame(DECK, random.Random(0))
    solo.new_game(Mode.SOLO, (None, None))
    assert solo.players == ["Você"]


def test_resolve_requires_two_cards() -> None:
    game = _game()
    game.flip(0)
    with pytest.raises(RuntimeError):
        game.resolve()
