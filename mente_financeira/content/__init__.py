"""Bancos de questões por trilha educacional.

Cada trilha fica em um arquivo ``<id>.toml`` nesta pasta. O carregador valida
o arquivo inteiro na leitura (gerando todas as questões de todos os cenários),
de modo que um erro de digitação no banco aparece imediatamente, com a fase e o
cenário indicados, e nunca no meio de uma partida.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from importlib import resources
import random
import tomllib
from typing import Any

from mente_financeira.content.calculators import CALCULATORS

TEMPLATE_FIELDS = ("question", "resolution", "explanation")


class ContentError(ValueError):
    """Erro de preenchimento em um banco de questões."""


@dataclass(frozen=True, slots=True)
class MemoryPair:
    pair_id: str
    question: str
    resolution: str
    explanation: str


@dataclass(frozen=True, slots=True)
class Phase:
    id: str
    title: str
    short_title: str
    objective: str
    calculator: str
    templates: Mapping[str, Mapping[str, str]]
    scenarios: tuple[Mapping[str, Any], ...]

    def render(self, scenario: Mapping[str, Any]) -> MemoryPair:
        kind = str(scenario.get("kind", "default"))
        template = self.templates.get(kind)
        if template is None:
            raise ContentError(f"{self.id}/{scenario.get('id')}: não há modelo de texto para o tipo '{kind}'.")
        try:
            values = {**scenario, **CALCULATORS[self.calculator](scenario)}
            texts = [template[field].format_map(values) for field in TEMPLATE_FIELDS]
        except KeyError as error:
            raise ContentError(f"{self.id}/{scenario.get('id')}: campo {error} ausente.") from error
        except (ValueError, ArithmeticError) as error:
            raise ContentError(f"{self.id}/{scenario.get('id')}: {error}") from error
        return MemoryPair(f"{self.id}-{scenario['id']}", *texts)


@dataclass(frozen=True, slots=True)
class Track:
    id: str
    name: str
    description: str
    pairs_per_phase: int
    phases: tuple[Phase, ...]

    def build_phase(self, index: int, rng: random.Random | None = None) -> list[MemoryPair]:
        """Sorteia os cenários de uma fase e devolve os pares prontos."""

        if not 0 <= index < len(self.phases):
            raise IndexError(f"Fase inexistente: {index}")
        phase = self.phases[index]
        chosen = (rng or random.Random()).sample(phase.scenarios, k=self.pairs_per_phase)
        return [phase.render(scenario) for scenario in chosen]


def _parse_phase(raw: Mapping[str, Any], pairs_per_phase: int) -> Phase:
    phase_id = raw.get("id", "?")
    try:
        phase = Phase(
            id=str(raw["id"]),
            title=str(raw["title"]),
            short_title=str(raw["short_title"]),
            objective=str(raw["objective"]),
            calculator=str(raw["calculator"]),
            templates=raw["templates"],
            scenarios=tuple(raw["scenarios"]),
        )
    except KeyError as error:
        raise ContentError(f"Fase {phase_id}: chave obrigatória {error} ausente.") from error

    if phase.calculator not in CALCULATORS:
        raise ContentError(f"Fase {phase.id}: calculador desconhecido '{phase.calculator}'.")
    for kind, template in phase.templates.items():
        missing = [field for field in TEMPLATE_FIELDS if field not in template]
        if missing:
            raise ContentError(f"Fase {phase.id}: modelo '{kind}' sem {', '.join(missing)}.")
    ids = [scenario.get("id") for scenario in phase.scenarios]
    if None in ids or len(set(ids)) != len(ids):
        raise ContentError(f"Fase {phase.id}: todo cenário precisa de um 'id' único.")
    if len(phase.scenarios) < pairs_per_phase:
        raise ContentError(
            f"Fase {phase.id}: são necessários pelo menos {pairs_per_phase} cenários; há {len(phase.scenarios)}."
        )
    for scenario in phase.scenarios:
        phase.render(scenario)
    return phase


def parse_track(data: Mapping[str, Any]) -> Track:
    try:
        pairs_per_phase = int(data["pairs_per_phase"])
        phases = tuple(_parse_phase(raw, pairs_per_phase) for raw in data["phases"])
        track = Track(str(data["id"]), str(data["name"]), str(data["description"]), pairs_per_phase, phases)
    except KeyError as error:
        raise ContentError(f"Trilha: chave obrigatória {error} ausente.") from error
    if not track.phases:
        raise ContentError(f"Trilha {track.id}: nenhuma fase cadastrada.")
    return track


@cache
def load_track(track_id: str) -> Track:
    """Lê e valida ``<track_id>.toml``. O resultado fica em cache."""

    source = resources.files(__package__).joinpath(f"{track_id}.toml")
    if not source.is_file():
        raise ContentError(f"Trilha inexistente: {track_id}")
    try:
        data = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ContentError(f"{track_id}.toml: {error}") from error
    return parse_track(data)


NON_TRACK_FILES = {"memoria"}  # baralho do jogo da memória, não é trilha


def available_tracks() -> list[str]:
    return sorted(
        name
        for entry in resources.files(__package__).iterdir()
        if entry.name.endswith(".toml") and (name := entry.name.removesuffix(".toml")) not in NON_TRACK_FILES
    )
