"""Desafio Relâmpago do Duelo online da feira: só perguntas de conceito.

O Duelo em sala (servidor_sala.py) tem três níveis: Ensino Fundamental, Médio
e Superior. Cada um sorteia do seu pedaço de content/banco_duelo_online.toml,
com perguntas simples, sem contas, pensadas para demonstrar o jogo. O sorteio
é o mesmo da Engenharia: sem repetir e alternando os assuntos.
"""

from __future__ import annotations

import random

from mente_financeira.content.question_bank import load_question_bank
from mente_financeira.core.engineering_challenge import QuestionBag
from mente_financeira.core.percent_challenge import ChallengeKit

FUNDAMENTAL, MEDIO, SUPERIOR = 1, 2, 3

# Completa "Desafio Relâmpago ..." nas regras do jogo.
LEVEL_TOPICS = {
    FUNDAMENTAL: "de dinheiro no dia a dia",
    MEDIO: "de educação financeira",
    SUPERIOR: "de engenharia econômica",
}

ENCOURAGEMENTS = (
    "Mandou muito! 🚀 Pode continuar.",
    "Cérebro financeiro ativado! 🧠💰",
    "Acertou em cheio! 🎯 A vez continua sua.",
    "Isso aí! Conceito dominado. 🔥",
    "Top! Seu eu do futuro agradece. 💸",
)


def encouragement(rng: random.Random | None = None) -> str:
    return (rng or random.Random()).choice(ENCOURAGEMENTS)


BANK = load_question_bank("banco_duelo_online")
CONCEPT_KITS = {
    level: ChallengeKit(topic, QuestionBag(q for q in BANK if q.level == level).make, encouragement)
    for level, topic in LEVEL_TOPICS.items()
}
