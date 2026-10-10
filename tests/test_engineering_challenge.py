"""Desafio Relâmpago da Engenharia de Produção (payback, valor presente e VPL)."""

from decimal import Decimal
from pathlib import Path
import random
import re

import pytest

from mente_financeira.core.engineering_challenge import (
    ENGINEERING_KIT,
    INVESTMENTS,
    KINDS,
    PROJECTS,
    RECEIPTS,
    make_challenge,
    signed_money,
)

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def _values(text: str) -> list[Decimal]:
    return [Decimal(m.replace(".", "").replace(",", ".")) for m in re.findall(r"R\$ ([\d.]+,\d{2})", text)]


def _rate(text: str) -> Decimal:
    return Decimal(re.search(r"TMA de (\d+)%", text)[1]) / 100


@pytest.mark.parametrize("kind", KINDS, ids=lambda k: k.__name__)
def test_every_kind_has_four_distinct_options(kind) -> None:
    for seed in range(400):
        c = kind(random.Random(seed))
        assert len(c.options) == 4 and len(set(c.options)) == 4
        assert c.answer in c.explanation
        assert c.label and c.item and (ASSETS / c.image).is_file()


def test_answers_are_right() -> None:
    for seed in range(600):
        c = make_challenge(random.Random(seed))
        numbers = _values(c.question)
        if c.label == "PAYBACK":
            cost, gain = numbers
            assert c.answer.startswith(f"{cost / gain:.0f} ")
        elif c.label == "VALOR PRESENTE":
            (future,) = numbers
            assert c.answer == signed_money(future / (1 + _rate(c.question)))
        else:  # VPL
            cost, future = numbers
            npv = future / (1 + _rate(c.question)) - cost
            assert c.answer == signed_money(npv)
            assert ("não vale a pena" in c.explanation) == (npv < 0)


def test_every_situation_is_used_and_has_an_image() -> None:
    keys = {item.key for item in INVESTMENTS}
    assert {key for key, _ in PROJECTS + RECEIPTS} <= keys
    for item in INVESTMENTS:
        assert (ASSETS / item.image).is_file(), item.image
        assert all(item.cost % gain == 0 for gain in item.gains), item.key  # payback inteiro
    images = {make_challenge(random.Random(seed)).image for seed in range(400)}
    assert images == {item.image for item in INVESTMENTS}


def test_negative_values_use_a_minus_sign() -> None:
    assert signed_money(Decimal(-1000)) == "−R$ 1.000,00"
    assert signed_money(Decimal(250)) == "R$ 250,00"


def test_kit_names_the_topic() -> None:
    assert ENGINEERING_KIT.topic == "de payback e VPL"
    assert ENGINEERING_KIT.encourage(random.Random(1))
