from decimal import Decimal
from pathlib import Path
import random
import re

import pytest

from mente_financeira.core.percent_challenge import ENCOURAGEMENTS, ITEMS, KINDS, encouragement, make_challenge


def _value(text: str) -> Decimal:
    return Decimal(text.removeprefix("R$ ").replace(".", "").replace(",", "."))


@pytest.mark.parametrize("kind", KINDS, ids=lambda k: k.__name__)
def test_every_kind_always_has_four_distinct_options(kind) -> None:
    for seed in range(400):
        challenge = kind(random.Random(seed))
        assert len(challenge.options) == 4
        assert len(set(challenge.options)) == 4
        assert challenge.answer in challenge.explanation
        for option in challenge.options:
            if option.startswith("R$"):
                assert _value(option) > 0


def test_answers_are_mathematically_correct() -> None:
    for seed in range(400):
        c = make_challenge(random.Random(seed))
        numbers = [_value(m) for m in re.findall(r"R\$ [\d.]+,\d{2}", c.question)]
        rate = int(re.search(r"(\d+)%", c.question)[1]) if "%" in c.question else None
        if "desconto" in c.question:
            assert _value(c.answer) == numbers[0] * (100 - rate) / 100
        elif "mais car" in c.question:
            assert _value(c.answer) == numbers[0] * (100 + rate) / 100
        elif "guardar" in c.question:
            assert _value(c.answer) == numbers[0] * rate / 100
        else:  # quantos por cento: "da mesada de R$ base, você gastou R$ parte"
            assert int(c.answer.removesuffix("%")) == numbers[1] / numbers[0] * 100


def test_results_are_whole_reais_for_mental_math() -> None:
    for seed in range(400):
        c = make_challenge(random.Random(seed))
        if c.answer.startswith("R$"):
            assert _value(c.answer) == _value(c.answer).to_integral_value()


def test_all_kinds_appear() -> None:
    questions = {make_challenge(random.Random(seed)).question.split()[0] for seed in range(200)}
    assert len(questions) >= 3


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def test_every_situation_has_label_item_and_existing_image() -> None:
    seen = set()
    for seed in range(600):
        c = make_challenge(random.Random(seed))
        assert c.label and c.item and c.image, c.question
        assert (ASSETS / c.image).is_file(), c.image
        seen.add(c.image)
    # todas as 17 ilustrações aparecem em algum sorteio
    assert seen == {f"desafios/{p.name}" for p in (ASSETS / "desafios").glob("*.svg")}


def test_price_increase_agrees_with_gender() -> None:
    for item in ITEMS:
        for seed in range(40):
            c = KINDS[2](random.Random(seed))
            if c.item != item.title:
                continue
            assert ("mais cara" in c.question) == item.feminine, c.question


def test_bills_never_get_cash_discount() -> None:
    for seed in range(400):
        c = KINDS[1](random.Random(seed))
        assert c.item not in ("Conta de luz", "Passe de ônibus")


def test_is_correct_and_encouragement() -> None:
    c = make_challenge(random.Random(1))
    assert c.is_correct(c.answer_index)
    assert not c.is_correct((c.answer_index + 1) % 4)
    assert encouragement(random.Random(2)) in ENCOURAGEMENTS
