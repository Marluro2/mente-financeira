"""Sugestões dos jogadores ("Deixe sua sugestão").

No site, o botão abre o Formulário Google do projeto (``FORM_URL``). Na feira,
sem internet, o Duelo em sala abre um formulário dentro do jogo e as respostas
vão para um arquivo CSV no notebook (abre no Excel).

Só pedimos a sugestão e, se a pessoa quiser, o nível de ensino e a idade:
nada de nome ou contato (LGPD e Comitê de Ética).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import threading

# Endereço do Formulário Google "Mente Financeira – Sugestões". Enquanto
# estiver vazio, o site não mostra o botão.
FORM_URL = ""

LEVELS = ("Ensino Fundamental 1", "Ensino Fundamental 2", "Ensino Médio")
TEXT_MAX = 500
AGE_MIN, AGE_MAX = 5, 99
COLUMNS = ("data_hora", "sugestao", "nivel", "idade")


class SuggestionError(ValueError):
    """Sugestão vazia ou longa demais, nível ou idade inválidos."""


@dataclass(frozen=True, slots=True)
class Suggestion:
    text: str
    level: str = ""
    age: int | None = None


def make_suggestion(text: str | None, level: str | None = None, age: str | int | None = None) -> Suggestion:
    text = " ".join((text or "").split())
    if len(text) < 3:
        raise SuggestionError("Escreva sua sugestão.")
    if len(text) > TEXT_MAX:
        raise SuggestionError(f"Use no máximo {TEXT_MAX} letras.")
    level = level or ""
    if level and level not in LEVELS:
        raise SuggestionError("Escolha um nível da lista.")
    number: int | None = None
    if age not in (None, ""):
        try:
            number = int(str(age).strip())
        except ValueError:
            raise SuggestionError("Digite a idade só com números.") from None
        if not AGE_MIN <= number <= AGE_MAX:
            raise SuggestionError(f"A idade precisa estar entre {AGE_MIN} e {AGE_MAX}.")
    return Suggestion(text, level, number)


class SuggestionBox:
    """Guarda as sugestões num CSV (uma linha por sugestão)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()  # vários celulares podem enviar ao mesmo tempo

    def save(self, suggestion: Suggestion, when: datetime | None = None) -> None:
        when = when or datetime.now()
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            new = not self.path.exists()
            # utf-8-sig: o Excel abre com os acentos certos.
            with self.path.open("a", newline="", encoding="utf-8-sig" if new else "utf-8") as file:
                writer = csv.writer(file, delimiter=";")
                if new:
                    writer.writerow(COLUMNS)
                writer.writerow(
                    (when.strftime("%d/%m/%Y %H:%M"), suggestion.text, suggestion.level, "" if suggestion.age is None else suggestion.age)
                )

    def read(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file, delimiter=";"))
