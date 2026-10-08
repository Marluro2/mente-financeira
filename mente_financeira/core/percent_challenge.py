"""Desafio Relâmpago: perguntas simples de porcentagem (Duelo do Nível 1).

Cada desafio é uma situação do dia a dia com imagem própria (assets/desafios).
Os valores são escolhidos para permitir cálculo mental (resultados inteiros).
As alternativas erradas imitam erros comuns: confundir o desconto com o preço
final, somar em vez de subtrair, errar a casa decimal etc.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
import random

from mente_financeira.finance import money

OPTIONS = 4
DISCOUNT, INCREASE = "desconto", "aumento"


@dataclass(frozen=True, slots=True)
class Item:
    key: str  # nome do arquivo em assets/desafios
    subject: str  # como aparece na pergunta, com artigo ("Uma camiseta")
    title: str  # rótulo curto exibido acima da pergunta
    price: int
    feminine: bool = False
    kinds: tuple[str, ...] = (DISCOUNT, INCREASE)

    @property
    def image(self) -> str:
        return f"desafios/{self.key}.svg"


ITEMS: tuple[Item, ...] = (
    Item("tenis", "Um tênis de corrida", "Tênis de corrida", 200),
    Item("fone", "Um fone de ouvido", "Fone de ouvido", 80),
    Item("ingresso_show", "Um ingresso de show", "Ingresso de show", 120),
    Item("camiseta", "Uma camiseta", "Camiseta", 60, feminine=True),
    Item("videogame", "Um jogo de videogame", "Jogo de videogame", 150),
    Item("mochila", "Uma mochila", "Mochila", 160, feminine=True),
    Item("lanche", "Um lanche", "Lanche", 40),
    Item("livro", "Um livro", "Livro", 50),
    Item("streaming", "Uma assinatura anual de streaming", "Assinatura de streaming", 240, feminine=True),
    Item("skate", "Um skate", "Skate", 300),
    # Situações do dia a dia
    Item("onibus", "O passe mensal de ônibus", "Passe de ônibus", 150, kinds=(INCREASE,)),
    Item("recarga_celular", "Uma recarga de celular", "Recarga de celular", 50, feminine=True),
    Item("conta_luz", "A conta de luz", "Conta de luz", 200, feminine=True, kinds=(INCREASE,)),
    Item("presente", "Um presente de aniversário", "Presente de aniversário", 80),
    Item("curso_online", "Um curso online", "Curso online", 300),
    Item("pizza", "Uma pizza", "Pizza", 60, feminine=True),
)

# Gastos usados em "quanto por cento da mesada?": (item, complemento da frase)
SPENDING: tuple[tuple[str, str], ...] = (
    ("lanche", "com lanches na escola"),
    ("recarga_celular", "com a recarga do celular"),
    ("pizza", "com uma pizza com os amigos"),
    ("ingresso_show", "com o ingresso de um show"),
    ("livro", "com um livro"),
    ("presente", "com o presente de um amigo"),
)
ALLOWANCE_IMAGE = "desafios/mesada.svg"

ALLOWANCES = (50, 80, 100, 150, 200)
RATES = (5, 10, 20, 25, 50)
WHAT_PERCENT_RATES = (10, 20, 25, 40, 50, 75)

ENCOURAGEMENTS = (
    "Mandou muito! 🚀 Pode continuar.",
    "Cérebro financeiro ativado! 🧠💰",
    "Isso aí! Porcentagem dominada. 🔥",
    "Você está on fire! Siga jogando. ⚡",
    "Acertou em cheio! 🎯 A vez continua sua.",
    "Top! Seu eu do futuro agradece. 💸",
    "Na mosca! Quem entende de porcentagem não cai em pegadinha. 😎",
)


@dataclass(frozen=True, slots=True)
class Challenge:
    question: str
    options: tuple[str, ...]
    answer_index: int
    explanation: str
    label: str = ""  # tipo de situação ("DESCONTO À VISTA")
    item: str = ""  # item em destaque ("Tênis de corrida")
    image: str = ""  # caminho em assets/

    @property
    def answer(self) -> str:
        return self.options[self.answer_index]

    def is_correct(self, index: int) -> bool:
        return index == self.answer_index


def _shuffle_options(answer: str, wrong: Iterable[str], rng: random.Random) -> tuple[tuple[str, ...], int]:
    """Junta a resposta a 3 alternativas erradas distintas e embaralha."""

    distinct: list[str] = []
    for option in wrong:
        if option != answer and option not in distinct:
            distinct.append(option)
    options = [answer, *distinct[: OPTIONS - 1]]
    if len(options) < OPTIONS:
        raise ValueError("Alternativas insuficientes para o desafio.")
    rng.shuffle(options)
    return tuple(options), options.index(answer)


def _money_options(answer: Decimal, wrong: Iterable[Decimal], rng: random.Random) -> tuple[tuple[str, ...], int]:
    # Reservas para quando as alternativas "de erro comum" coincidem entre si
    # (ex.: 50% de desconto, em que desconto e preço final são iguais).
    fallback = (answer + 10, answer + 5, answer * 2, answer - 5)
    candidates = [*wrong, *fallback]
    return _shuffle_options(money(answer), (money(value) for value in candidates if value > 0), rng)


def _whole_percent(rng: random.Random, prices: tuple[int, ...], rates: tuple[int, ...]) -> tuple[int, int, Decimal]:
    """Sorteia (preço, taxa, valor da porcentagem) com resultado inteiro."""

    while True:
        price, rate = rng.choice(prices), rng.choice(rates)
        if price * rate % 100 == 0:
            return price, rate, Decimal(price * rate) / 100


def _item_for(rng: random.Random, kind: str) -> Item:
    return rng.choice([item for item in ITEMS if kind in item.kinds])


def _percent_of(rng: random.Random) -> Challenge:
    base, rate, amount = _whole_percent(rng, ALLOWANCES, RATES)
    options, index = _money_options(amount, [amount / 10, base - amount, amount * 2, base + amount], rng)
    return Challenge(
        f"Você ganha {money(base)} de mesada e decide guardar {rate}%. Quanto vai guardar?",
        options,
        index,
        f"{rate}% de {money(base)} = {money(base)} × {rate} ÷ 100 = {money(amount)}.",
        label="PLANEJANDO A MESADA",
        item="Mesada",
        image=ALLOWANCE_IMAGE,
    )


def _discount(rng: random.Random) -> Challenge:
    item = _item_for(rng, DISCOUNT)
    price, rate, amount = _whole_percent(rng, (item.price,), RATES)
    final = price - amount
    options, index = _money_options(final, [amount, price + amount, price - 2 * amount, price - amount / 10], rng)
    return Challenge(
        f"{item.subject} custa {money(price)} e está com {rate}% de desconto à vista. Quanto você paga?",
        options,
        index,
        f"Desconto: {rate}% de {money(price)} = {money(amount)}.\nVocê paga {money(price)} − {money(amount)} = {money(final)}.",
        label="DESCONTO À VISTA",
        item=item.title,
        image=item.image,
    )


def _increase(rng: random.Random) -> Challenge:
    item = _item_for(rng, INCREASE)
    price, rate, amount = _whole_percent(rng, (item.price,), RATES)
    final = price + amount
    options, index = _money_options(final, [amount, price - amount, price + 2 * amount, price + amount / 10], rng)
    pricier = "mais cara" if item.feminine else "mais caro"
    return Challenge(
        f"{item.subject} custava {money(price)} e ficou {rate}% {pricier}. Qual é o novo preço?",
        options,
        index,
        f"Aumento: {rate}% de {money(price)} = {money(amount)}.\nNovo preço: {money(price)} + {money(amount)} = {money(final)}.",
        label="AUMENTO DE PREÇO",
        item=item.title,
        image=item.image,
    )


def _what_percent(rng: random.Random) -> Challenge:
    base, rate, part = _whole_percent(rng, ALLOWANCES, WHAT_PERCENT_RATES)
    key, phrase = rng.choice(SPENDING)
    item = next(i for i in ITEMS if i.key == key)
    others = [f"{r}%" for r in (5, 10, 15, 20, 25, 30, 40, 50, 60, 75)]
    rng.shuffle(others)
    options, index = _shuffle_options(f"{rate}%", others, rng)
    fraction = str((part / base).quantize(Decimal("0.01"))).replace(".", ",")
    return Challenge(
        f"Da sua mesada de {money(base)}, você gastou {money(part)} {phrase}. Isso é quantos por cento da mesada?",
        options,
        index,
        f"{money(part)} ÷ {money(base)} = {fraction} = {rate}%.",
        label="QUANTO POR CENTO?",
        item=item.title,
        image=item.image,
    )


KINDS: tuple[Callable[[random.Random], Challenge], ...] = (_percent_of, _discount, _increase, _what_percent)


def make_challenge(rng: random.Random | None = None) -> Challenge:
    rng = rng or random.Random()
    return rng.choice(KINDS)(rng)


def encouragement(rng: random.Random | None = None) -> str:
    return (rng or random.Random()).choice(ENCOURAGEMENTS)


@dataclass(frozen=True, slots=True)
class ChallengeKit:
    """Desafio Relâmpago que o Duelo de uma trilha usa."""

    topic: str  # completa "Desafio Relâmpago ..." nas regras ("de porcentagem")
    make: Callable[[random.Random], Challenge]
    encourage: Callable[[random.Random], str]


PERCENT_KIT = ChallengeKit("de porcentagem", make_challenge, encouragement)
