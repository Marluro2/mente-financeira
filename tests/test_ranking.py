"""Ranking da feira: melhores apelidos do dia, só na memória."""

from __future__ import annotations

from mente_financeira.sala.ranking import DUEL, QUIZ, TOP, FairRanking


def test_each_nickname_keeps_its_best_result() -> None:
    ranking = FairRanking()
    assert ranking.record(DUEL, 1, [("Lia", 80), ("Theo", 120)], "Ensino Fundamental 1")
    assert ranking.record(DUEL, 2, [("lia", 150), ("Theo", 60)], "Engenharia de Produção")
    top = ranking.top(DUEL)
    assert [(e.nickname, e.points, e.detail) for e in top] == [
        ("lia", 150, "Engenharia de Produção"),
        ("Theo", 120, "Ensino Fundamental 1"),
    ]
    assert ranking.top(QUIZ) == []


def test_the_same_game_counts_once_and_zero_points_stay_out() -> None:
    ranking = FairRanking()
    assert ranking.record(QUIZ, 1, [("Ana", 900), ("Bia", 0)], "Ensino Fundamental 2")
    assert not ranking.record(QUIZ, 1, [("Ana", 5000)], "Ensino Fundamental 2")
    assert ranking.record(DUEL, 1, [("Ana", 40)], "Ensino Fundamental 2")  # outro placar, mesmo número
    assert [(e.nickname, e.points) for e in ranking.top(QUIZ)] == [("Ana", 900)]


def test_top_is_limited_and_ties_go_alphabetically() -> None:
    ranking = FairRanking()
    ranking.record(QUIZ, 1, [(f"P{n:02d}", 100 + n // 2) for n in range(15)], "x")
    top = ranking.top(QUIZ)
    assert len(top) == TOP
    assert [e.nickname for e in top[:3]] == ["P14", "P12", "P13"]


def test_staff_can_remove_a_nickname_or_clear_everything() -> None:
    ranking = FairRanking()
    ranking.record(DUEL, 1, [("Lia", 80), ("Theo", 120)], "x")
    assert ranking.remove(DUEL, "THEO")
    assert not ranking.remove(DUEL, "Theo") and not ranking.remove("outro", "Lia")
    assert ranking.as_dict() == {"duelo": [{"nickname": "Lia", "points": 80, "detail": "x"}], "quiz": []}
    ranking.clear()
    assert ranking.as_dict() == {"duelo": [], "quiz": []}
