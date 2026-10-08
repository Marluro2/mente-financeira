from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from mente_financeira.content import ContentError, available_tracks
from mente_financeira.content.memory_deck import load_memory_deck, parse_deck

ASSETS = Path(__file__).resolve().parents[1] / "assets"
DECK = load_memory_deck()
# Baralhos do Ensino Fundamental 2 (memoria) e do Ensino Fundamental 1.
DECK_NAMES = ("memoria", "memoria_fundamental1")
DECKS = [load_memory_deck(name) for name in DECK_NAMES]


@pytest.mark.parametrize("deck", DECKS, ids=DECK_NAMES)
def test_deck_has_enough_concepts_for_variety(deck) -> None:
    assert deck.pairs == 8
    assert len(deck.concepts) >= deck.pairs + 2  # partidas variam
    assert len({c.id for c in deck.concepts}) == len(deck.concepts)


@pytest.mark.parametrize("image", sorted({d.back_image for d in DECKS} | {c.image for d in DECKS for c in d.concepts}))
def test_every_image_exists_and_is_valid_svg(image: str) -> None:
    path = ASSETS / image
    assert path.is_file(), f"imagem ausente: {image}"
    root = ET.parse(path).getroot()
    assert root.tag.endswith("svg")
    assert root.get("viewBox") == "0 0 200 200"


@pytest.mark.parametrize("deck", DECKS, ids=DECK_NAMES)
def test_images_live_in_the_cards_folder(deck) -> None:
    assert all(c.image.startswith("cartas/") for c in deck.concepts)


@pytest.mark.parametrize("deck", DECKS, ids=DECK_NAMES)
def test_tips_are_short_enough_for_a_phone(deck) -> None:
    for concept in deck.concepts:
        assert 30 <= len(concept.tip) <= 170, concept.id
        assert 40 <= len(concept.example) <= 200, concept.id
        assert len(concept.name) <= 22, concept.id


@pytest.mark.parametrize("deck", DECKS, ids=DECK_NAMES)
def test_every_example_has_numbers(deck) -> None:
    # "Na prática" deve trazer uma situação concreta, com valores.
    for concept in deck.concepts:
        assert any(ch.isdigit() for ch in concept.example), concept.id


def test_memory_decks_are_not_listed_as_tracks() -> None:
    assert not set(DECK_NAMES) & set(available_tracks())


def test_fundamental1_has_no_percent() -> None:
    # Crianças de 7 a 10 anos: só soma e subtração, sem porcentagem.
    deck = load_memory_deck("memoria_fundamental1")
    assert len(deck.concepts) == 12
    assert not any("%" in c.tip + c.example for c in deck.concepts)


def _deck(**overrides) -> dict:
    concept = {"id": "a", "name": "A", "image": "cartas/a.svg", "color": "#112233", "tip": "Dica.", "example": "Ex. 1."}
    data = {"pairs": 1, "back_image": "cartas/verso.svg", "concepts": [concept]}
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"pairs": 2}, "pelo menos 2"),
        ({"concepts": [{"id": "a", "name": "A", "image": "x", "color": "vermelho", "tip": "D.", "example": "E."}]}, "cor inválida"),
        ({"concepts": [{"id": "a", "name": "A", "image": "x", "color": "#112233", "tip": " ", "example": "E."}]}, "nome, dica e exemplo"),
        ({"concepts": [{"id": "a", "name": "A", "image": "x", "color": "#112233", "tip": "D.", "example": ""}]}, "nome, dica e exemplo"),
        ({"concepts": [{"id": "a", "name": "A", "image": "x", "color": "#112233", "example": "E."}]}, "'tip'"),
        ({"concepts": [{"id": "a", "name": "A", "image": "x", "color": "#112233", "tip": "D."}]}, "'example'"),
    ],
)
def test_deck_errors_are_reported(overrides: dict, message: str) -> None:
    with pytest.raises(ContentError, match=message):
        parse_deck(_deck(**overrides))


def test_deck_errors_name_the_file() -> None:
    with pytest.raises(ContentError, match="memoria_fundamental1.toml"):
        parse_deck(_deck(pairs=2), "memoria_fundamental1.toml")
