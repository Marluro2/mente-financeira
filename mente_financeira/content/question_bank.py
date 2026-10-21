"""Banco de questões objetivas da Engenharia de Produção (``banco_engenharia.toml``).

São perguntas prontas, com a alternativa certa, três erradas e uma explicação,
separadas por nível (1 a 3) e por assunto. O Desafio Relâmpago da Engenharia
sorteia daqui (veja core/engineering_challenge.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib import resources
import tomllib

from mente_financeira.content import ContentError

LEVELS = (1, 2, 3)


@dataclass(frozen=True, slots=True)
class Topic:
    level: int
    name: str
    label: str  # rótulo em destaque acima da pergunta ("PAYBACK")
    image: str  # caminho relativo à pasta assets/


@dataclass(frozen=True, slots=True)
class BankQuestion:
    id: str
    level: int
    topic: Topic
    item: str  # título curto da situação ("Robô de solda")
    question: str
    answer: str
    wrong: tuple[str, ...]
    explanation: str


def parse_question_bank(data: dict, source: str = "banco_engenharia.toml") -> tuple[BankQuestion, ...]:
    try:
        topics = {
            str(raw["name"]): Topic(int(raw["level"]), str(raw["name"]), str(raw["label"]), str(raw["image"]))
            for raw in data["topics"]
        }
        questions = []
        for raw in data["questions"]:
            name = str(raw["topic"])
            if name not in topics:
                raise ContentError(f"{source}: questão {raw.get('id')} usa o assunto '{name}', que não está em [[topics]].")
            questions.append(
                BankQuestion(
                    id=str(raw["id"]),
                    level=int(raw["level"]),
                    topic=topics[name],
                    item=str(raw["item"]),
                    question=str(raw["question"]),
                    answer=str(raw["answer"]),
                    wrong=tuple(str(option) for option in raw["wrong"]),
                    explanation=str(raw["explanation"]),
                )
            )
    except KeyError as error:
        raise ContentError(f"{source}: chave obrigatória {error} ausente.") from error

    ids = [q.id for q in questions]
    if len(set(ids)) != len(ids):
        raise ContentError(f"{source}: há questões com 'id' repetido.")
    for q in questions:
        options = (q.answer, *q.wrong)
        if len(q.wrong) != 3 or len(set(options)) != 4:
            raise ContentError(f"{source}: a questão {q.id} precisa de 1 resposta e 3 alternativas erradas, todas diferentes.")
        if q.level not in LEVELS or q.topic.level != q.level:
            raise ContentError(f"{source}: a questão {q.id} está no nível {q.level}, mas o assunto é do nível {q.topic.level}.")
        if not all(text.strip() for text in (q.item, q.question, q.explanation, *options)):
            raise ContentError(f"{source}: a questão {q.id} tem um campo vazio.")
    for level in LEVELS:
        if not any(q.level == level for q in questions):
            raise ContentError(f"{source}: o nível {level} não tem questões.")
    return tuple(questions)


@cache
def load_question_bank(name: str = "banco_engenharia") -> tuple[BankQuestion, ...]:
    source = f"{name}.toml"
    with resources.files("mente_financeira.content").joinpath(source).open("rb") as handle:
        return parse_question_bank(tomllib.load(handle), source)
