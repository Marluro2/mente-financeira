"""Baralhos da Memória Financeira.

``memoria.toml`` é o do Ensino Fundamental 2 e ``memoria_fundamental1.toml``
o do Ensino Fundamental 1. Os dois têm o mesmo formato. No da Engenharia de
Produção (``memoria_engenharia.toml``), cada carta diz também o seu nível.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib import resources
import re
import tomllib

from mente_financeira.content import ContentError

_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True, slots=True)
class Concept:
    id: str
    name: str
    image: str  # caminho relativo à pasta assets/
    color: str
    tip: str
    example: str  # situação do dia a dia com números
    level: int | None = None  # nível da Engenharia em que a carta aparece


@dataclass(frozen=True, slots=True)
class MemoryDeck:
    pairs: int
    back_image: str
    concepts: tuple[Concept, ...]

    @property
    def levels(self) -> tuple[int, ...]:
        return tuple(sorted({c.level for c in self.concepts if c.level is not None}))

    def for_level(self, level: int) -> MemoryDeck:
        """Só as cartas de um nível; sem nível (Duelo online, quiz), vale o baralho todo."""

        concepts = tuple(c for c in self.concepts if c.level == level)
        if len(concepts) < self.pairs:
            raise ContentError(f"o nível {level} tem {len(concepts)} cartas; são necessárias {self.pairs}.")
        return MemoryDeck(self.pairs, self.back_image, concepts)


def parse_deck(data: dict, source: str = "memoria.toml") -> MemoryDeck:
    try:
        concepts = tuple(
            Concept(
                id=str(raw["id"]),
                name=str(raw["name"]),
                image=str(raw["image"]),
                color=str(raw["color"]),
                tip=str(raw["tip"]),
                example=str(raw["example"]),
                level=int(raw["level"]) if "level" in raw else None,
            )
            for raw in data["concepts"]
        )
        deck = MemoryDeck(int(data["pairs"]), str(data["back_image"]), concepts)
    except KeyError as error:
        raise ContentError(f"{source}: chave obrigatória {error} ausente.") from error

    ids = [concept.id for concept in deck.concepts]
    if len(set(ids)) != len(ids):
        raise ContentError(f"{source}: há conceitos com 'id' repetido.")
    if len(deck.concepts) < deck.pairs:
        raise ContentError(f"{source}: são necessários pelo menos {deck.pairs} conceitos; há {len(deck.concepts)}.")
    for level in deck.levels:
        count = sum(1 for concept in deck.concepts if concept.level == level)
        if count < deck.pairs:
            raise ContentError(f"{source}: o nível {level} tem {count} cartas; são necessárias pelo menos {deck.pairs}.")
    for concept in deck.concepts:
        if not concept.name.strip() or not concept.tip.strip() or not concept.example.strip():
            raise ContentError(f"{source}: o conceito '{concept.id}' precisa de nome, dica e exemplo.")
        if not _HEX_COLOR.match(concept.color):
            raise ContentError(f"{source}: cor inválida em '{concept.id}' (use #RRGGBB).")
    return deck


@cache
def load_memory_deck(name: str = "memoria") -> MemoryDeck:
    """Lê e valida ``<name>.toml``. O resultado fica em cache."""

    filename = f"{name}.toml"
    source = resources.files(__package__).joinpath(filename)
    try:
        return parse_deck(tomllib.loads(source.read_text(encoding="utf-8")), filename)
    except tomllib.TOMLDecodeError as error:
        raise ContentError(f"{filename}: {error}") from error
