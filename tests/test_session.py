import random

import pytest

from mente_financeira.content import load_track
from mente_financeira.core import DEFAULT_PLAYERS, QUESTION, RESOLUTION, GameSession, Selection


@pytest.fixture
def session() -> GameSession:
    game = GameSession(load_track("medio"), random.Random(42), timer_seconds=90)
    game.new_game()
    return game


def _wrong_resolution(game: GameSession, question_id: str) -> str:
    return next(pid for pid in game.resolution_order if pid != question_id)


def _play_match(game: GameSession, pair_id: str) -> None:
    assert game.select(QUESTION, pair_id) is Selection.OPENED
    assert game.select(RESOLUTION, pair_id) is Selection.READY
    assert game.resolve().matched
    game.resume_timer()


def test_new_game_starts_on_first_phase(session: GameSession) -> None:
    assert session.phase_index == 0
    assert session.scores == [0, 0]
    assert session.phase_active
    assert sorted(session.question_order) == sorted(session.resolution_order)
    assert len(session.pairs) == session.track.pairs_per_phase


def test_player_names_are_cleaned(session: GameSession) -> None:
    session.set_players("  Ana   Clara ", "")
    assert session.players == ["Ana Clara", DEFAULT_PLAYERS[1]]
    session.set_players("x" * 60, None)
    assert session.players[0] == "x" * 24


def test_must_start_with_a_question(session: GameSession) -> None:
    pid = session.resolution_order[0]
    assert session.select(RESOLUTION, pid) is Selection.NEED_QUESTION
    session.select(QUESTION, session.question_order[0])
    assert session.select(QUESTION, session.question_order[1]) is Selection.NEED_RESOLUTION


def test_match_scores_and_keeps_the_turn(session: GameSession) -> None:
    pid = session.question_order[0]
    session.select(QUESTION, pid)
    assert session.select(RESOLUTION, pid) is Selection.READY
    assert session.locked
    assert session.select(QUESTION, session.question_order[1]) is Selection.IGNORED

    outcome = session.resolve()
    assert outcome.matched and outcome.pair is not None and outcome.pair.pair_id == pid
    assert session.scores == [1, 0]
    assert session.turn == 0
    assert session.timer_paused
    assert not session.locked
    assert session.select(QUESTION, pid) is Selection.IGNORED  # já encontrada


def test_miss_passes_the_turn_and_counts_mistake(session: GameSession) -> None:
    pid = session.question_order[0]
    session.select(QUESTION, pid)
    session.select(RESOLUTION, _wrong_resolution(session, pid))
    assert not session.resolve().matched
    assert session.turn == 1
    assert session.scores == [0, 0]
    assert session.phase_mistakes == session.total_mistakes == 1


def test_timer_pauses_and_expires(session: GameSession) -> None:
    session.timer_paused = True
    assert session.tick() is False
    assert session.time_left == 90
    session.resume_timer()
    session.time_left = 2
    assert session.tick() is False
    assert session.tick() is True
    assert not session.phase_active and session.locked
    assert session.tick() is False  # o fim do tempo é informado uma única vez


def test_repeat_phase_undoes_points_of_the_attempt(session: GameSession) -> None:
    _play_match(session, session.question_order[0])
    assert session.scores == [1, 0]
    session.start_phase(repeat=True)
    assert session.scores == [0, 0]


def test_full_phase_gives_three_stars_and_allows_advance(session: GameSession) -> None:
    for pid in list(session.question_order):
        _play_match(session, pid)
    assert session.is_phase_complete
    summary = session.finish_phase()
    assert summary.stars == 3 and summary.mistakes == 0
    assert session.advance_available
    assert session.advance()
    assert session.phase_index == 1
    assert session.scores == [4, 0]
    assert session.phase_start_scores == [4, 0]


def test_cannot_advance_before_finishing(session: GameSession) -> None:
    assert not session.advance()
    assert session.phase_index == 0


def test_last_phase_does_not_advance_and_reports_winner(session: GameSession) -> None:
    session.phase_index = session.phase_count - 1
    session.start_phase(repeat=False)
    for pid in list(session.question_order):
        _play_match(session, pid)
    session.finish_phase()
    assert session.is_last_phase
    assert not session.advance()
    assert session.final_result() == f"{session.players[0]} venceu!"


def test_star_rules() -> None:
    game = GameSession(load_track("medio"), random.Random(1), timer_seconds=100)
    game.new_game()
    game.time_left, game.phase_mistakes = 20, 5
    assert game.finish_phase().stars == 1
    game.time_left, game.phase_mistakes = 40, 5
    assert game.finish_phase().stars == 2
