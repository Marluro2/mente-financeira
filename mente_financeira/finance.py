"""Fórmulas de matemática financeira e formatação no padrão brasileiro.

O módulo não depende da interface gráfica. Todos os cálculos usam ``Decimal``
para evitar o erro binário típico de ``float``.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

Numeric = Decimal | int | float | str

CENT = Decimal("0.01")


def decimal(value: Numeric) -> Decimal:
    """Converte valores sem introduzir o erro binário típico de ``float``."""

    return value if isinstance(value, Decimal) else Decimal(str(value))


def round_money(value: Numeric) -> Decimal:
    return decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def money(value: Numeric) -> str:
    """Formata um valor monetário no padrão brasileiro."""

    formatted = f"{round_money(value):,.2f}"
    formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {formatted}"


def number(value: Numeric, digits: int = 2) -> str:
    quantizer = Decimal(1).scaleb(-digits)
    formatted = f"{decimal(value).quantize(quantizer, rounding=ROUND_HALF_UP):.{digits}f}"
    return formatted.replace(".", ",")


def percent(rate: Numeric, digits: int = 2) -> str:
    return f"{number(decimal(rate) * 100, digits)}%"


def simple_interest_amount(capital: Numeric, rate: Numeric, periods: int) -> Decimal:
    if periods < 0:
        raise ValueError("O número de períodos não pode ser negativo.")
    c, i = decimal(capital), decimal(rate)
    return c * (Decimal(1) + i * periods)


def compound_interest_amount(capital: Numeric, rate: Numeric, periods: int) -> Decimal:
    if periods < 0:
        raise ValueError("O número de períodos não pode ser negativo.")
    c, i = decimal(capital), decimal(rate)
    return c * (Decimal(1) + i) ** periods


def commercial_discount_net(nominal: Numeric, discount_rate: Numeric, periods: int) -> Decimal:
    if periods < 0:
        raise ValueError("O número de períodos não pode ser negativo.")
    n, d = decimal(nominal), decimal(discount_rate)
    result = n * (Decimal(1) - d * periods)
    if result < 0:
        raise ValueError("A taxa e o prazo produzem valor líquido negativo.")
    return result


def monthly_to_annual(rate: Numeric) -> Decimal:
    i = decimal(rate)
    if i <= Decimal("-1"):
        raise ValueError("A taxa mensal deve ser maior que -100%.")
    return (Decimal(1) + i) ** 12 - Decimal(1)


def price_payment(principal: Numeric, rate: Numeric, periods: int) -> Decimal:
    if periods <= 0:
        raise ValueError("O número de parcelas deve ser positivo.")
    p, i = decimal(principal), decimal(rate)
    if i == 0:
        return p / periods
    factor = (Decimal(1) + i) ** periods
    return p * (i * factor) / (factor - Decimal(1))
