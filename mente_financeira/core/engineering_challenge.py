"""Desafio Relâmpago da Engenharia de Produção: payback, valor presente e VPL.

Mesma ideia dos outros desafios (uma pergunta rápida a cada par no Duelo),
agora com decisões de investimento de uma fábrica ou de um pequeno negócio.
Os valores são escolhidos para a conta fechar de cabeça (resultados inteiros).
As alternativas erradas imitam erros comuns: tirar a porcentagem do valor
futuro em vez de dividir por (1 + i), esquecer de descontar o tempo, esquecer
de subtrair o investimento, trocar o sinal do VPL.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
import random

from mente_financeira.core.percent_challenge import Challenge, ChallengeKit, _shuffle_options
from mente_financeira.finance import money

MONTHS, YEARS = "meses", "anos"


@dataclass(frozen=True, slots=True)
class Investment:
    key: str  # nome do arquivo em assets/desafios/engenharia
    title: str  # rótulo curto exibido acima da pergunta
    payback: str  # frase do payback, com {cost} e {gain}
    cost: int
    gains: tuple[int, ...]  # ganhos por período; cost é múltiplo de todos
    unit: str = MONTHS

    @property
    def image(self) -> str:
        return f"desafios/engenharia/{self.key}.svg"


INVESTMENTS: tuple[Investment, ...] = (
    Investment(
        "placa_solar",
        "Placas solares",
        "Placas solares custam {cost} e economizam {gain} por mês na conta de luz.",
        12_000,
        (200, 250, 300, 400),
    ),
    Investment(
        "lampada_led",
        "Iluminação LED",
        "Trocar as lâmpadas da fábrica por LED custa {cost} e economiza {gain} por mês de energia.",
        3_600,
        (150, 200, 300, 400),
    ),
    Investment(
        "maquina",
        "Máquina nova",
        "Uma máquina nova custa {cost} e aumenta o lucro da fábrica em {gain} por ano.",
        60_000,
        (10_000, 12_000, 15_000, 20_000),
        unit=YEARS,
    ),
    Investment(
        "impressora_3d",
        "Impressora 3D",
        "Uma impressora 3D de {cost} dá {gain} de lucro por mês com peças sob encomenda.",
        4_800,
        (200, 300, 400, 600),
    ),
    Investment(
        "food_truck",
        "Food truck",
        "Um food truck custa {cost} e dá {gain} de lucro por mês.",
        90_000,
        (3_000, 4_500, 5_000, 6_000),
    ),
    Investment(
        "carro_app",
        "Carro de aplicativo",
        "Um carro de {cost} para trabalhar com aplicativo dá {gain} de lucro por mês.",
        48_000,
        (2_000, 2_400, 3_000, 4_000),
    ),
)

# Investimentos de "qual é o VPL?": (item, frase com {cost} e {future}).
PROJECTS: tuple[tuple[str, str], ...] = (
    ("maquina", "Uma máquina custa {cost} e vai gerar {future} de lucro daqui a 1 ano."),
    ("impressora_3d", "Uma impressora 3D custa {cost} e vai gerar {future} com encomendas daqui a 1 ano."),
    ("food_truck", "Reformar o food truck custa {cost} e vai trazer {future} a mais daqui a 1 ano."),
)

# Recebimentos futuros de "quanto vale hoje?": (item, frase com {future}).
RECEIPTS: tuple[tuple[str, str], ...] = (
    ("maquina", "Um cliente da fábrica vai pagar {future} daqui a 1 ano."),
    ("food_truck", "Um evento vai pagar {future} ao seu food truck daqui a 1 ano."),
    ("impressora_3d", "Uma escola encomendou peças da sua impressora 3D e vai pagar {future} daqui a 1 ano."),
)

PRESENT_VALUES = (1_000, 2_000, 5_000, 10_000, 20_000)
RATES = (5, 10, 20, 25)  # TMA em % ao ano: (1 + i) × valor inteiro dá valor inteiro

ENCOURAGEMENTS = (
    "Mandou muito! 🚀 Pode continuar.",
    "Decisão de engenheiro! 📈 A vez continua sua.",
    "Investimento bem analisado! 🏭",
    "Na mosca! 🎯 Quem calcula antes não se arrepende depois.",
    "Cérebro financeiro ativado! 🧠💰",
    "Show! Payback e VPL não têm segredo para você. ⭐",
)


def _investment(key: str) -> Investment:
    return next(item for item in INVESTMENTS if item.key == key)


def signed_money(value: Decimal) -> str:
    """Valor com sinal: "R$ 1.000,00" ou "−R$ 1.000,00"."""

    return f"−{money(-value)}" if value < 0 else money(value)


def _factor(rate: int) -> str:
    """1 + i escrito como no Brasil: 10% → "1,10"."""

    return f"1,{rate:02d}"


def _money_options(answer: Decimal, wrong: Iterable[Decimal], rng: random.Random) -> tuple[tuple[str, ...], int]:
    fallback = (answer + 1000, answer - 1000, answer * 2, answer + 500)
    return _shuffle_options(signed_money(answer), (signed_money(v) for v in [*wrong, *fallback]), rng)


def _payback(rng: random.Random) -> Challenge:
    item = rng.choice(INVESTMENTS)
    gain = rng.choice(item.gains)
    periods = item.cost // gain
    unit = item.unit

    def text(n: int) -> str:
        return f"{n} {unit}" if n != 1 else ("1 mês" if unit == MONTHS else "1 ano")

    step = 6 if unit == MONTHS else 1
    others = [text(n) for n in (periods * 2, periods + step, periods - step, periods // 2, periods + 2 * step) if n > 0]
    options, index = _shuffle_options(text(periods), others, rng)
    in_years = f" ({periods // 12} anos)" if unit == MONTHS and periods % 12 == 0 else ""
    per = "por mês" if unit == MONTHS else "por ano"
    return Challenge(
        item.payback.format(cost=money(item.cost), gain=money(gain)) + f" Em quantos {unit} o investimento se paga?",
        options,
        index,
        f"Payback = investimento ÷ ganho {per}.\n{money(item.cost)} ÷ {money(gain)} = {text(periods)}{in_years}.",
        label="PAYBACK",
        item=item.title,
        image=item.image,
    )


def _present_value(rng: random.Random) -> Challenge:
    key, phrase = rng.choice(RECEIPTS)
    item = _investment(key)
    today, rate = Decimal(rng.choice(PRESENT_VALUES)), rng.choice(RATES)
    future = today * (100 + rate) / 100
    options, index = _money_options(
        today,
        [future * (100 - rate) / 100, future, today * (100 - rate) / 100, future * (100 + rate) / 100],
        rng,
    )
    return Challenge(
        phrase.format(future=money(future)) + f" Com TMA de {rate}% ao ano, quanto esse valor vale hoje?",
        options,
        index,
        f"Valor de hoje = valor futuro ÷ (1 + TMA).\n{money(future)} ÷ {_factor(rate)} = {money(today)}.",
        label="VALOR PRESENTE",
        item=item.title,
        image=item.image,
    )


def _npv(rng: random.Random) -> Challenge:
    key, phrase = rng.choice(PROJECTS)
    item = _investment(key)
    today, rate = Decimal(rng.choice(PRESENT_VALUES[1:])), rng.choice(RATES)
    future = today * (100 + rate) / 100
    cost = today - today * rng.choice((-2, -1, 1, 2)) / 20  # VPL de ±5% ou ±10% do valor de hoje
    npv = today - cost
    options, index = _money_options(npv, [future - cost, -npv, today, future * (100 - rate) / 100 - cost], rng)
    verdict = "positivo, o investimento vale a pena" if npv > 0 else "negativo, o investimento não vale a pena"
    return Challenge(
        phrase.format(cost=money(cost), future=money(future)) + f" Com TMA de {rate}% ao ano, qual é o VPL?",
        options,
        index,
        f"Valor de hoje: {money(future)} ÷ {_factor(rate)} = {money(today)}.\n"
        f"VPL = {money(today)} − {money(cost)} = {signed_money(npv)}: {verdict}.",
        label="VPL: VALE A PENA?",
        item=item.title,
        image=item.image,
    )


KINDS = (_payback, _present_value, _npv)


def make_challenge(rng: random.Random | None = None) -> Challenge:
    rng = rng or random.Random()
    return rng.choice(KINDS)(rng)


def encouragement(rng: random.Random | None = None) -> str:
    return (rng or random.Random()).choice(ENCOURAGEMENTS)


ENGINEERING_KIT = ChallengeKit("de payback e VPL", make_challenge, encouragement)
