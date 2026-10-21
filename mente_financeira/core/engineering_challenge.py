"""Desafio Relâmpago da Engenharia de Produção: banco de questões por nível.

As questões vêm de content/banco_engenharia.toml (40 por nível). Cada nível
escolhido na página de níveis tem o seu kit; o Duelo online e o quiz do telão,
que não têm escolha de nível, usam as 120 misturadas.

As questões saem sem repetir: só depois de usar todas é que uma volta, e a
ordem alterna os assuntos, para uma partida não trazer três de payback seguidas.
"""

from __future__ import annotations

from collections.abc import Iterable
import random
from weakref import WeakKeyDictionary

from mente_financeira.content.question_bank import BankQuestion, Topic, load_question_bank
from mente_financeira.core.percent_challenge import Challenge, ChallengeKit, _shuffle_options

# Completa "Desafio Relâmpago ..." nas regras do jogo.
LEVEL_TOPICS = {
    1: "de fundamentos e custos",
    2: "de avaliação de investimentos",
    3: "de operações e decisões",
}

ENCOURAGEMENTS = (
    "Mandou muito! 🚀 Pode continuar.",
    "Decisão de engenheiro! 📈 A vez continua sua.",
    "Investimento bem analisado! 🏭",
    "Na mosca! 🎯 Quem calcula antes não se arrepende depois.",
    "Cérebro financeiro ativado! 🧠💰",
    "Show! Engenharia econômica não tem segredo para você. ⭐",
)


def to_challenge(question: BankQuestion, rng: random.Random) -> Challenge:
    """Questão do banco no formato do Desafio Relâmpago, com as alternativas embaralhadas."""

    options, index = _shuffle_options(question.answer, question.wrong, rng)
    return Challenge(
        question.question,
        options,
        index,
        question.explanation,
        label=question.topic.label,
        item=question.item,
        image=question.topic.image,
    )


class QuestionBag:
    """Sorteia questões sem repetir, alternando os assuntos.

    Cada sorteador (``random.Random``) tem a sua fila: o jogo usa um por janela
    aberta, então quem joga várias partidas seguidas só revê uma questão depois
    de passar por todas.
    """

    def __init__(self, questions: Iterable[BankQuestion]) -> None:
        self.questions = tuple(questions)
        self._queues: WeakKeyDictionary[random.Random, list[BankQuestion]] = WeakKeyDictionary()

    def make(self, rng: random.Random) -> Challenge:
        queue = self._queues.setdefault(rng, [])
        if len(queue) < 2:  # emenda a próxima volta antes do fim, sabendo o último assunto
            queue.extend(self._round(rng, queue[-1].topic if queue else None))
        return to_challenge(queue.pop(0), rng)

    def _round(self, rng: random.Random, last: Topic | None = None) -> list[BankQuestion]:
        by_topic: dict[str, list[BankQuestion]] = {}
        for question in self.questions:
            by_topic.setdefault(question.topic.name, []).append(question)
        piles = list(by_topic.values())
        for pile in piles:
            rng.shuffle(pile)
        # Uma de cada assunto por vez, em ordem sorteada a cada rodada, sem o
        # mesmo assunto duas vezes seguidas na virada de uma rodada para outra.
        order: list[BankQuestion] = []
        for turn in range(max(map(len, piles))):
            row = [pile[turn] for pile in piles if turn < len(pile)]
            rng.shuffle(row)
            if len(row) > 1 and row[0].topic == (order[-1].topic if order else last):
                row[0], row[-1] = row[-1], row[0]
            order.extend(row)
        return order


def encouragement(rng: random.Random | None = None) -> str:
    return (rng or random.Random()).choice(ENCOURAGEMENTS)


def _kit(topic: str, questions: Iterable[BankQuestion]) -> ChallengeKit:
    return ChallengeKit(topic, QuestionBag(questions).make, encouragement)


BANK = load_question_bank()
ENGINEERING_LEVEL_KITS = {level: _kit(topic, (q for q in BANK if q.level == level)) for level, topic in LEVEL_TOPICS.items()}
ENGINEERING_KIT = _kit("de engenharia econômica", BANK)  # sem nível: Duelo online e quiz do telão
