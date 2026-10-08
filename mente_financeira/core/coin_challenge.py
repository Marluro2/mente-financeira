"""Desafio Relâmpago do Ensino Fundamental 1: contas de dinheiro sem porcentagem.

Mesma ideia do desafio de porcentagem do Ensino Fundamental 2 (uma pergunta
rápida a cada par no Duelo), mas com o que crianças de 7 a 10 anos já fazem de
cabeça: troco, soma de compras, sobra da mesada e semanas para juntar. Os
valores são pequenos e inteiros. As alternativas erradas imitam erros comuns:
somar em vez de subtrair, repetir um dos números da pergunta, errar por um.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import random

from mente_financeira.core.percent_challenge import (
    ALLOWANCE_IMAGE,
    Challenge,
    ChallengeKit,
    _money_options,
    _shuffle_options,
)
from mente_financeira.finance import money

NOTES = (5, 10, 20, 50)


@dataclass(frozen=True, slots=True)
class Item:
    key: str  # nome do arquivo em assets/desafios
    subject: str  # como aparece na pergunta, com artigo ("Um lanche")
    title: str  # rótulo curto exibido acima da pergunta
    price: int

    @property
    def image(self) -> str:
        return f"desafios/{self.key}.svg"


ITEMS: tuple[Item, ...] = (
    Item("lanche", "Um lanche", "Lanche", 6),
    Item("livro", "Um livro", "Livro", 12),
    Item("presente", "Um presente", "Presente", 15),
    Item("camiseta", "Uma camiseta", "Camiseta", 18),
    Item("pizza", "Uma pizza", "Pizza", 24),
    Item("mochila", "Uma mochila", "Mochila", 35),
)

# Objetivos para "quantas semanas para juntar": (item, valor guardado por semana).
# O preço é sempre múltiplo do valor semanal, para a conta dar exata.
GOALS: tuple[tuple[str, int], ...] = (
    ("livro", 3),
    ("livro", 4),
    ("presente", 3),
    ("presente", 5),
    ("camiseta", 3),
    ("camiseta", 6),
    ("pizza", 4),
    ("pizza", 6),
    ("mochila", 5),
    ("mochila", 7),
)

ALLOWANCES = (10, 15, 20, 30)

ENCOURAGEMENTS = (
    "Mandou muito! 🚀 Pode continuar.",
    "Cérebro financeiro ativado! 🧠💰",
    "Isso aí! Conta certinha. 🔥",
    "Acertou em cheio! 🎯 A vez continua sua.",
    "Muito bem! Quem confere o troco não perde dinheiro. 😎",
    "Show! Você é fera nas contas. ⭐",
)


def _item(key: str) -> Item:
    return next(item for item in ITEMS if item.key == key)


def _change(rng: random.Random) -> Challenge:
    item = rng.choice(ITEMS)
    note = rng.choice([n for n in NOTES if n > item.price])
    change = Decimal(note - item.price)
    options, index = _money_options(change, [Decimal(item.price), Decimal(note + item.price), change + 1, change - 1], rng)
    return Challenge(
        f"{item.subject} custa {money(item.price)}. Você paga com uma nota de {money(note)}. Quanto recebe de troco?",
        options,
        index,
        f"Troco: {money(note)} − {money(item.price)} = {money(change)}.",
        label="CONFIRA O TROCO",
        item=item.title,
        image=item.image,
    )


def _total(rng: random.Random) -> Challenge:
    first, second = rng.sample([item for item in ITEMS if item.price <= 18], k=2)
    total = Decimal(first.price + second.price)
    options, index = _money_options(
        total, [Decimal(abs(first.price - second.price)), Decimal(second.price), total + 1, total + 10], rng
    )
    return Challenge(
        f"Você comprou {first.subject.lower()} de {money(first.price)} e {second.subject.lower()} de "
        f"{money(second.price)}. Quanto gastou ao todo?",
        options,
        index,
        f"Total: {money(first.price)} + {money(second.price)} = {money(total)}.",
        label="SOMANDO AS COMPRAS",
        item=f"{first.title} e {second.title.lower()}",
        image=first.image,
    )


def _left_over(rng: random.Random) -> Challenge:
    allowance = rng.choice(ALLOWANCES)
    item = rng.choice([item for item in ITEMS if item.price < allowance])
    left = Decimal(allowance - item.price)
    options, index = _money_options(
        left, [Decimal(item.price), Decimal(allowance + item.price), left + 1, left - 1], rng
    )
    return Challenge(
        f"Sua mesada é de {money(allowance)} e você gastou {money(item.price)} com {item.subject.lower()}. Quanto sobrou?",
        options,
        index,
        f"Sobra: {money(allowance)} − {money(item.price)} = {money(left)}.",
        label="O QUE SOBROU DA MESADA",
        item="Mesada",
        image=ALLOWANCE_IMAGE,
    )


def _weeks(rng: random.Random) -> Challenge:
    key, per_week = rng.choice(GOALS)
    item = _item(key)
    weeks = item.price // per_week

    def text(n: int) -> str:
        return f"{n} semana" if n == 1 else f"{n} semanas"

    others = [text(n) for n in (weeks - 1, weeks + 1, weeks + 2, item.price, weeks - 2) if n > 0]
    options, index = _shuffle_options(text(weeks), others, rng)
    return Challenge(
        f"{item.subject} custa {money(item.price)}. Guardando {money(per_week)} por semana, "
        "em quantas semanas você junta o dinheiro?",
        options,
        index,
        f"{money(item.price)} ÷ {money(per_week)} = {text(weeks)}, porque {weeks} × {money(per_week)} = {money(item.price)}.",
        label="JUNTANDO PARA UM OBJETIVO",
        item=item.title,
        image=item.image,
    )


KINDS = (_change, _total, _left_over, _weeks)


def make_challenge(rng: random.Random | None = None) -> Challenge:
    rng = rng or random.Random()
    return rng.choice(KINDS)(rng)


def encouragement(rng: random.Random | None = None) -> str:
    return (rng or random.Random()).choice(ENCOURAGEMENTS)


COIN_KIT = ChallengeKit("de contas com dinheiro", make_challenge, encouragement)
