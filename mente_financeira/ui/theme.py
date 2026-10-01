"""Paletas de cores do jogo."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Palette:
    name: str
    primary: str
    secondary: str
    light_background: str
    light_surface: str
    dark_background: str
    dark_surface: str
    on_primary: str = "#FFFFFF"


PALETTES: dict[str, Palette] = {
    "kids": Palette("Kids", "#6552D0", "#FFB000", "#FFF8ED", "#FFFFFF", "#17132A", "#26203C"),
    "neon": Palette("Neon", "#006D77", "#FF4D8D", "#ECFEFF", "#FFFFFF", "#061A1D", "#0C2A2F"),
    "pastel": Palette("Pastel", "#7B5EA7", "#D9779F", "#FAF7FC", "#FFFFFF", "#211A2B", "#30263D"),
}

DEFAULT_PALETTE = "kids"
