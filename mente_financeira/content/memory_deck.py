"""Baralho da Memória Financeira (arquivo ``memoria.toml``)."""

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


@dataclass(frozen=True, slots=True)
class MemoryDeck:
    pairs: int
    back_image: str
    concepts: tuple[Concept, ...]


def parse_deck(data: dict) -> MemoryDeck:
    try:
        concepts = tuple(
            Concept(
                id=str(raw["id"]),
                name=str(raw["name"]),
                image=str(raw["image"]),
                color=str(raw["color"]),
                tip=str(raw["tip"]),
                example=str(raw["example"]),
            )
            for raw in data["concepts"]
        )
        deck = MemoryDeck(int(data["pairs"]), str(data["back_image"]), concepts)
    except KeyError as error:
        raise ContentError(f"memoria.toml: chave obrigatória {error} ausente.") from error

    ids = [concept.id for concept in deck.concepts]
    if len(set(ids)) != len(ids):
        raise ContentError("memoria.toml: há conceitos com 'id' repetido.")
    if len(deck.concepts) < deck.pairs:
        raise ContentError(f"memoria.toml: são necessários pelo menos {deck.pairs} conceitos; há {len(deck.concepts)}.")
    for concept in deck.concepts:
        if not concept.name.strip() or not concept.tip.strip() or not concept.example.strip():
            raise ContentError(f"memoria.toml: o conceito '{concept.id}' precisa de nome, dica e exemplo.")
        if not _HEX_COLOR.match(concept.color):
            raise ContentError(f"memoria.toml: cor inválida em '{concept.id}' (use #RRGGBB).")
    return deck


@cache
def load_memory_deck() -> MemoryDeck:
    source = resources.files(__package__).joinpath("memoria.toml")
    try:
        return parse_deck(tomllib.loads(source.read_text(encoding="utf-8")))
    except tomllib.TOMLDecodeError as error:
        raise ContentError(f"memoria.toml: {error}") from error
