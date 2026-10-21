"""Duelo online da feira: três níveis, só perguntas de conceito."""

from collections import Counter
from pathlib import Path
import random
import re

from mente_financeira.core.concept_challenge import BANK, CONCEPT_KITS
from mente_financeira.sala.app import DUEL_LEVELS

ASSETS = Path(__file__).resolve().parents[1] / "assets"
BY_QUESTION = {q.question: q for q in BANK}


def test_bank_has_20_questions_per_level() -> None:
    assert Counter(q.level for q in BANK) == {1: 20, 2: 20, 3: 20}
    assert len({q.question for q in BANK}) == len(BANK)


def test_questions_are_conceptual_and_fit_the_buttons() -> None:
    for q in BANK:
        options = (q.answer, *q.wrong)
        assert not any(re.search(r"\d", text) for text in options), q.id  # nenhuma alternativa pede conta
        assert all(len(option) <= 36 for option in options), q.id
        assert (ASSETS / q.topic.image).is_file(), q.topic.image


def test_each_duel_level_asks_only_its_own_questions() -> None:
    assert [level.title for level in DUEL_LEVELS] == ["Ensino Fundamental", "Ensino Médio", "Ensino Superior"]
    for number, level in enumerate(DUEL_LEVELS, start=1):
        assert level.challenges is CONCEPT_KITS[number]
        rng = random.Random(number)
        asked = [level.challenges.make(rng).question for _ in range(20)]
        assert len(set(asked)) == 20  # uma volta inteira sem repetir
        assert {BY_QUESTION[q].level for q in asked} == {number}
