"""Desafio Relâmpago do Ensino Fundamental 1 (troco, soma, sobra e semanas)."""

from decimal import Decimal
from pathlib import Path
import random
import re

import pytest

from mente_financeira.core.coin_challenge import COIN_KIT, ENCOURAGEMENTS, KINDS, make_challenge

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def _values(text: str) -> list[Decimal]:
    return [Decimal(m.replace(".", "").replace(",", ".")) for m in re.findall(r"R\$ ([\d.]+,\d{2})", text)]


@pytest.mark.parametrize("kind", KINDS, ids=lambda k: k.__name__)
def test_every_kind_has_four_distinct_positive_options(kind) -> None:
    for seed in range(400):
        c = kind(random.Random(seed))
        assert len(c.options) == 4 and len(set(c.options)) == 4
        assert c.answer in c.explanation
        assert all(int(re.search(r"\d+", option)[0]) > 0 for option in c.options)
        assert "%" not in c.question
        assert c.label and c.item and (ASSETS / c.image).is_file()


def test_answers_are_right() -> None:
    for seed in range(400):
        c = make_challenge(random.Random(seed))
        numbers = _values(c.question)
        if "troco" in c.question:
            answer = numbers[1] - numbers[0]
        elif "ao todo" in c.question:
            answer = numbers[0] + numbers[1]
        elif "sobrou" in c.question:
            answer = numbers[0] - numbers[1]
        else:  # semanas para juntar
            assert c.answer == f"{numbers[0] / numbers[1]:.0f} semanas"
            continue
        assert _values(c.answer) == [answer]
        assert answer == answer.to_integral_value() and answer > 0


def test_all_kinds_appear_and_kit_is_wired() -> None:
    labels = {make_challenge(random.Random(seed)).label for seed in range(200)}
    assert len(labels) == len(KINDS)
    assert COIN_KIT.make is make_challenge
    assert COIN_KIT.encourage(random.Random(1)) in ENCOURAGEMENTS
    assert "porcentagem" not in " ".join(ENCOURAGEMENTS).lower()
