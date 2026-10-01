from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from mente_financeira.content import ContentError, available_tracks
from mente_financeira.content.memory_deck import load_memory_deck, parse_deck

ASSETS = Path(__file__).resolve().parents[1] / "assets"
DECK = load_memory_deck()


def test_deck_has_enough_concepts_for_variety() -> None:
    assert DECK.pairs == 8
    assert len(DECK.concepts) >= DECK.pairs + 2  # partidas variam
    assert len({c.id for c in DECK.concepts}) == len(DECK.concepts)


@pytest.mark.parametrize("image", [DECK.back_image, *(c.image for c in DECK.concepts)])
def test_every_image_exists_and_is_valid_svg(image: str) -> None:
    path = ASSETS / image
    assert path.is_file(), f"imagem ausente: {image}"
    root = ET.parse(path).getroot()
    assert root.tag.endswith("svg")
    assert root.get("viewBox") == "0 0 200 200"


def test_images_live_in_the_cards_folder() -> None:
    assert all(c.image.startswith("cartas/") for c in DECK.concepts)


def test_tips_are_short_enough_for_a_phone() -> None:
    for concept in DECK.concepts:
        assert 30 <= len(concept.tip) <= 170, concept.id
        assert 40 <= len(concept.example) <= 200, concept.id
        assert len(concept.name) <= 22, concept.id


def test_every_example_has_numbers() -> None:
    # "Na prática" deve trazer uma situação concreta, com valores.
    for concept in DECK.concepts:
        assert any(ch.isdigit() for ch in concept.example), concept.id


def test_memory_deck_is_not_listed_as_a_track() -> None:
    assert "memoria" not in available_tracks()


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
