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
    net_present_value,
    number,
    percent,
    price_payment,
    round_money,
    simple_interest_amount,
    simple_payback,
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


def _rate(i: Decimal) -> str:
    """Taxa curta para o enunciado: 10% ou 12,5%."""

    return percent(i, 0) if (i * 100) == (i * 100).to_integral_value() else percent(i, 1)


def payback(scenario: Scenario) -> dict[str, str]:
    investment, gain = decimal(scenario["investment"]), decimal(scenario["gain"])
    months = simple_payback(investment, gain)
    if months != months.to_integral_value():
        raise ValueError("Escolha valores com payback em meses inteiros.")
    n = int(months)
    in_years = f" ({n // 12} {'ano' if n == 12 else 'anos'})" if n % 12 == 0 else ""
    return {
        "investment": money(investment),
        "gain": money(gain),
        "periods": f"{n} {_months(n)}",
        "in_years": in_years,
    }


def _flows_text(flows: list[Decimal]) -> str:
    """ "R$ 8.000,00 por ano durante 3 anos" ou "R$ 20.000,00, R$ 25.000,00 e R$ 30.000,00 nos anos 1, 2 e 3"."""

    n = len(flows)
    if len(set(flows)) == 1:
        return f"{money(flows[0])} por ano" + ("" if n == 1 else f" durante {n} anos")
    values = [money(flow) for flow in flows]
    years = [str(t) for t in range(1, n + 1)]
    return f"{', '.join(values[:-1])} e {values[-1]} nos anos {', '.join(years[:-1])} e {years[-1]}"


def npv(scenario: Scenario) -> dict[str, str]:
    investment, i = decimal(scenario["investment"]), decimal(scenario["rate"])
    flows = [decimal(flow) for flow in scenario["flows"]]
    if not 1 <= len(flows) <= 5:
        raise ValueError("Use de 1 a 5 fluxos de caixa (anos).")
    value = round_money(net_present_value(investment, flows, i))
    factor = number(Decimal(1) + i, 2 if (i * 100) == (i * 100).to_integral_value() else 3)
    terms = " + ".join(
        f"{money(flow)} ÷ {factor}" + ("" if t == 1 else f"{'²³⁴⁵'[t - 2]}") for t, flow in enumerate(flows, start=1)
    )
    sign = "−" if value < 0 else ""
    return {
        "investment": money(investment),
        "rate": _rate(i),
        "flows": _flows_text(flows),
        "terms": terms,
        "npv": f"{sign}{money(abs(value))}",
        "verdict": "vale a pena" if value > 0 else "não vale a pena",
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
    "payback": payback,
    "npv": npv,
}
