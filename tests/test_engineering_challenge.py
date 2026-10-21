"""Desafio Relâmpago da Engenharia de Produção: banco de questões por nível."""

from collections import Counter
from pathlib import Path
import random

import pytest

from mente_financeira.content import ContentError
from mente_financeira.content.question_bank import load_question_bank, parse_question_bank
from mente_financeira.core.engineering_challenge import (
    BANK,
    ENGINEERING_KIT,
    ENGINEERING_LEVEL_KITS,
    QuestionBag,
    to_challenge,
)
from mente_financeira.core.medals import NPV_LABEL

ASSETS = Path(__file__).resolve().parents[1] / "assets"
BY_QUESTION = {q.question: q for q in BANK}


def test_bank_has_40_questions_per_level_and_10_per_topic() -> None:
    assert len(BANK) == 120
    assert Counter(q.level for q in BANK) == {1: 40, 2: 40, 3: 40}
    topics = Counter(q.topic.name for q in BANK)
    assert len(topics) == 12 and set(topics.values()) == {10}
    assert len({q.question for q in BANK}) == 120  # nenhuma pergunta repetida


def test_every_question_is_ready_for_the_game() -> None:
    for q in BANK:
        options = (q.answer, *q.wrong)
        assert len(set(options)) == 4, q.id
        assert all(len(option) <= 36 for option in options), q.id  # cabe no botão
        assert q.explanation and q.item, q.id
        assert (ASSETS / q.topic.image).is_file(), q.topic.image


def test_level_kits_only_ask_their_own_level() -> None:
    for level, kit in ENGINEERING_LEVEL_KITS.items():
        rng = random.Random(level)
        for _ in range(60):
            assert BY_QUESTION[kit.make(rng).question].level == level


def test_questions_do_not_repeat_until_all_were_asked() -> None:
    kit = ENGINEERING_LEVEL_KITS[2]
    rng = random.Random(7)
    first = [kit.make(rng).question for _ in range(40)]
    assert len(set(first)) == 40
    second = [kit.make(rng).question for _ in range(40)]
    assert set(second) == set(first)  # na segunda volta, as mesmas em outra ordem
    assert second != first


def test_topics_alternate() -> None:
    for kit in (*ENGINEERING_LEVEL_KITS.values(), ENGINEERING_KIT):
        rng = random.Random(3)
        topics = [BY_QUESTION[kit.make(rng).question].topic.name for _ in range(130)]
        assert all(a != b for a, b in zip(topics, topics[1:]))


def test_each_game_window_has_its_own_queue() -> None:
    bag = QuestionBag(q for q in BANK if q.level == 1)
    a, b = random.Random(1), random.Random(1)
    assert [bag.make(a).question for _ in range(5)] == [bag.make(b).question for _ in range(5)]


def test_challenge_shuffles_the_options_and_keeps_the_answer() -> None:
    question = BANK[0]
    seen = set()
    for seed in range(30):
        c = to_challenge(question, random.Random(seed))
        assert c.answer == question.answer
        assert sorted(c.options) == sorted((question.answer, *question.wrong))
        assert c.label == question.topic.label and c.item == question.item
        seen.add(c.answer_index)
    assert len(seen) > 1


def test_npv_questions_carry_the_medal_label() -> None:
    npv = [q for q in BANK if q.topic.label == NPV_LABEL]
    assert len(npv) == 10 and all(q.level == 2 for q in npv)


def test_mixed_kit_uses_all_levels() -> None:
    rng = random.Random(5)
    levels = {BY_QUESTION[ENGINEERING_KIT.make(rng).question].level for _ in range(12)}
    assert levels == {1, 2, 3}
    assert ENGINEERING_KIT.encourage(random.Random(1))


def test_bad_bank_is_refused() -> None:
    data = {
        "topics": [{"level": 1, "name": "A", "label": "A", "image": "a.svg"}],
        "questions": [
            {"id": "1", "level": 1, "topic": "A", "item": "x", "question": "?", "answer": "1", "wrong": ["1", "2", "3"], "explanation": "e"}
        ],
    }
    with pytest.raises(ContentError, match="todas diferentes"):
        parse_question_bank(data)
    data["questions"][0]["wrong"] = ["2", "3", "4"]
    with pytest.raises(ContentError, match="nível 2 não tem"):
        parse_question_bank(data)
    assert load_question_bank() is BANK
