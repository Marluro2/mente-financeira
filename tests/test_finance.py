from decimal import Decimal

import pytest

from mente_financeira.finance import (
    commercial_discount_net,
    compound_interest_amount,
    money,
    monthly_to_annual,
    percent,
    price_payment,
    round_money,
    simple_interest_amount,
)


def test_financial_formulas() -> None:
    assert simple_interest_amount(500, "0.02", 6) == Decimal("560.00")
    assert round_money(compound_interest_amount(300, "0.02", 6)) == Decimal("337.85")
    assert commercial_discount_net(1000, "0.02", 2) == Decimal("960.00")
    assert round_money(monthly_to_annual("0.01")) == Decimal("0.13")
    assert round_money(price_payment(300, "0.02", 6)) == Decimal("53.56")


def test_price_with_zero_rate_splits_evenly() -> None:
    assert price_payment(600, 0, 6) == Decimal("100")


def test_brazilian_formatting() -> None:
    assert money("1234.5") == "R$ 1.234,50"
    assert money("0") == "R$ 0,00"
    assert percent("0.015") == "1,50%"
    assert percent("0.15", 0) == "15%"


def test_invalid_financial_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        simple_interest_amount(100, "0.02", -1)
    with pytest.raises(ValueError):
        price_payment(100, "0.02", 0)
    with pytest.raises(ValueError):
        commercial_discount_net(100, "0.5", 3)
    with pytest.raises(ValueError):
        monthly_to_annual("-1")


def test_payback_and_net_present_value() -> None:
    from mente_financeira.finance import net_present_value, simple_payback

    assert simple_payback(12_000, 250) == 48
    assert net_present_value(9_000, [12_100], "0.10") == Decimal(2_000)
    assert net_present_value(10_000, [0, 12_100], "0.10") == 0
    with pytest.raises(ValueError):
        simple_payback(1_000, 0)
