"""Calculadores que transformam um cenário do banco de questões em valores.

Cada calculador recebe os campos de um cenário (lidos do arquivo TOML) e
devolve os valores já formatados que os modelos de texto podem usar, como
``{base}``, ``{rate}`` ou ``{final}``. Para criar um novo tipo de questão,
basta escrever um calculador e registrá-lo em ``CALCULATORS``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any

from mente_financeira.finance import (
    commercial_discount_net,
    compound_interest_amount,
    decimal,
    money,
    monthly_to_annual,
    number,
    percent,
    price_payment,
    round_money,
    simple_interest_amount,
)

Scenario = Mapping[str, Any]
Calculator = Callable[[Scenario], dict[str, str]]


def _months(periods: int) -> str:
    return "mês" if periods == 1 else "meses"


def _financed(scenario: Scenario) -> str:
    return "financiada" if scenario.get("feminine", False) else "financiado"


def percentage(scenario: Scenario) -> dict[str, str]:
    base, rate = decimal(scenario["base"]), decimal(scenario["rate"])
    amount = base * rate
    match scenario["kind"]:
        case "discount":
            final = base - amount
        case "tip" | "increase":
            final = base + amount
        case "commission":
            final = amount
        case other:
            raise ValueError(f"Tipo de porcentagem desconhecido: {other}")
    return {"base": money(base), "rate": percent(rate, 0), "amount": money(amount), "final": money(final)}


def simple_interest(scenario: Scenario) -> dict[str, str]:
    c, i, n = decimal(scenario["capital"]), decimal(scenario["rate"]), int(scenario["periods"])
    return {
        "capital": money(c),
        "rate": percent(i),
        "rate_decimal": number(i, 4),
        "periods": str(n),
        "months": _months(n),
        "amount": money(simple_interest_amount(c, i, n)),
    }


def compound_interest(scenario: Scenario) -> dict[str, str]:
    c, i, n = decimal(scenario["capital"]), decimal(scenario["rate"]), int(scenario["periods"])
    return {
        "capital": money(c),
        "rate": percent(i),
        "rate_decimal": number(i, 4),
        "periods": str(n),
        "months": _months(n),
        "amount": money(compound_interest_amount(c, i, n)),
    }


def commercial_discount(scenario: Scenario) -> dict[str, str]:
    nominal, d, n = decimal(scenario["nominal"]), decimal(scenario["rate"]), int(scenario["periods"])
    return {
        "nominal": money(nominal),
        "rate": percent(d),
        "rate_decimal": number(d, 4),
        "periods": str(n),
        "months": _months(n),
        "net": money(commercial_discount_net(nominal, d, n)),
    }


def rate_equivalence(scenario: Scenario) -> dict[str, str]:
    monthly = decimal(scenario["rate"])
    return {
        "monthly": percent(monthly),
        "monthly_decimal": number(monthly, 4),
        "annual": percent(monthly_to_annual(monthly)),
    }


def inflation(scenario: Scenario) -> dict[str, str]:
    price, pi = decimal(scenario["price"]), decimal(scenario["inflation"])
    return {
        "price": money(price),
        "inflation": percent(pi),
        "inflation_decimal": number(pi, 4),
        "corrected": money(price * (Decimal(1) + pi)),
    }


def price_installment(scenario: Scenario) -> dict[str, str]:
    p, i, n = decimal(scenario["principal"]), decimal(scenario["rate"]), int(scenario["periods"])
    return {
        "principal": money(p),
        "rate": percent(i),
        "rate_decimal": number(i, 4),
        "periods": str(n),
        "financed": _financed(scenario),
        "payment": money(price_payment(p, i, n)),
    }


def price_total(scenario: Scenario) -> dict[str, str]:
    p, i, n = decimal(scenario["principal"]), decimal(scenario["rate"]), int(scenario["periods"])
    # Na prática cada parcela é cobrada em centavos; o total parte da
    # prestação já arredondada para que a conta da explicação feche.
    payment = round_money(price_payment(p, i, n))
    return {
        "principal": money(p),
        "rate": percent(i),
        "periods": str(n),
        "financed": _financed(scenario),
        "payment": money(payment),
        "total": money(payment * n),
    }


CALCULATORS: dict[str, Calculator] = {
    "percentage": percentage,
    "simple_interest": simple_interest,
    "compound_interest": compound_interest,
    "commercial_discount": commercial_discount,
    "rate_equivalence": rate_equivalence,
    "inflation": inflation,
    "price_installment": price_installment,
    "price_total": price_total,
}
