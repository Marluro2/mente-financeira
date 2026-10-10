from decimal import Decimal
import random
import re

import pytest

from mente_financeira.content import ContentError, MemoryPair, available_tracks, load_track, parse_track

TRACK = load_track("medio")
PHASE_INDEXES = range(len(TRACK.phases))


def _all_pairs(phase_index: int) -> list[MemoryPair]:
    phase = TRACK.phases[phase_index]
    return [phase.render(scenario) for scenario in phase.scenarios]


def test_medio_track_is_available() -> None:
    assert "medio" in available_tracks()
    assert len(TRACK.phases) == 8
    assert TRACK.pairs_per_phase == 4


@pytest.mark.parametrize("phase_index", PHASE_INDEXES)
def test_every_phase_builds_complete_pairs(phase_index: int) -> None:
    pairs = TRACK.build_phase(phase_index, random.Random(100 + phase_index))
    assert len(pairs) == TRACK.pairs_per_phase
    assert len({pair.pair_id for pair in pairs}) == len(pairs)
    for pair in pairs:
        assert pair.question.strip() and pair.resolution.strip() and pair.explanation.strip()
        assert "{" not in pair.question + pair.resolution + pair.explanation


def test_phase_index_is_validated() -> None:
    with pytest.raises(IndexError):
        TRACK.build_phase(-1)
    with pytest.raises(IndexError):
        TRACK.build_phase(len(TRACK.phases))


@pytest.mark.parametrize("phase_index", PHASE_INDEXES)
def test_explanation_ends_with_the_resolution_value(phase_index: int) -> None:
    for pair in _all_pairs(phase_index):
        value = pair.resolution.split(": ", 1)[1].removesuffix(" a.a.")
        assert value in pair.explanation, pair.pair_id


def test_price_total_is_consistent_with_the_rounded_payment() -> None:
    for pair in _all_pairs(7):
        match = re.search(r"= R\$ ([\d.,]+) × (\d+) = R\$ ([\d.,]+)", pair.explanation)
        assert match, pair.pair_id
        payment, periods, total = (
            Decimal(match[1].replace(".", "").replace(",", ".")),
            int(match[2]),
            Decimal(match[3].replace(".", "").replace(",", ".")),
        )
        assert payment * periods == total, pair.pair_id


@pytest.mark.parametrize("phase_index", PHASE_INDEXES)
def test_questions_have_proper_articles(phase_index: int) -> None:
    for pair in _all_pairs(phase_index):
        assert "(a)" not in pair.question, pair.question
        assert not re.search(r"\bEm uma (desconto|pagamento|investimento|fundo)\b", pair.question), pair.question
        assert not re.search(r"\b(Um|Uma|um|uma) (Um|Uma|um|uma)\b", pair.question), pair.question
        assert "1 meses" not in pair.question, pair.question


# --------------------------------------------------- validação do banco TOML
def _minimal_track(**phase_overrides: object) -> dict:
    phase = {
        "id": "x1",
        "title": "Fase teste",
        "short_title": "Teste",
        "objective": "Testar.",
        "calculator": "rate_equivalence",
        "templates": {
            "default": {
                "question": "{context}: {monthly} a.m.?",
                "resolution": "Taxa: {annual}",
                "explanation": "= {annual}",
            }
        },
        "scenarios": [{"id": "a", "context": "A", "rate": "0.01"}, {"id": "b", "context": "B", "rate": "0.02"}],
    }
    phase.update(phase_overrides)
    return {"id": "t", "name": "Teste", "description": "", "pairs_per_phase": 2, "phases": [phase]}


def test_minimal_track_is_valid() -> None:
    track = parse_track(_minimal_track())
    assert [pair.pair_id for pair in track.build_phase(0, random.Random(0))] in (["x1-a", "x1-b"], ["x1-b", "x1-a"])


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"calculator": "inexistente"}, "calculador desconhecido"),
        ({"scenarios": [{"id": "a", "context": "A", "rate": "0.01"}]}, "pelo menos 2"),
        ({"scenarios": [{"id": "a", "rate": "0.01"}, {"id": "b", "rate": "0.02"}]}, "campo 'context' ausente"),
        ({"scenarios": [{"id": "a", "context": "A", "rate": "0.01"}] * 2}, "'id' único"),
        ({"templates": {"default": {"question": "?"}}}, "sem resolution, explanation"),
    ],
)
def test_content_errors_point_to_the_problem(overrides: dict, message: str) -> None:
    with pytest.raises(ContentError, match=message):
        parse_track(_minimal_track(**overrides))


def test_unknown_track_is_reported() -> None:
    with pytest.raises(ContentError):
        load_track("nao_existe")


# ------------------------------------------------------------ Engenharia de Produção
ENGINEERING = load_track("engenharia")


def test_engineering_track_has_payback_and_npv_phases() -> None:
    assert "engenharia" in available_tracks()
    assert [phase.calculator for phase in ENGINEERING.phases] == ["payback", "npv"]
    for index, phase in enumerate(ENGINEERING.phases):
        pairs = [phase.render(scenario) for scenario in phase.scenarios]
        # Respostas diferentes: no jogo da memória cada resolução tem um só par.
        assert len({pair.resolution for pair in pairs}) == len(pairs)
        assert len(ENGINEERING.build_phase(index, random.Random(index))) == ENGINEERING.pairs_per_phase


def test_engineering_answers_are_right() -> None:
    payback, npv = ENGINEERING.phases
    robot = payback.render(next(s for s in payback.scenarios if s["id"] == "robot"))
    assert robot.resolution == "Payback: 24 meses" and "(2 anos)" in robot.explanation
    line = npv.render(next(s for s in npv.scenarios if s["id"] == "line"))
    # −100.000 + 40.000/1,1 + 40.000/1,1² + 40.000/1,1³ = −525,92
    assert line.resolution == "VPL: −R$ 525,92 (não vale a pena)"
    assert "R$ 40.000,00 por ano durante 3 anos" in line.question
    oven = npv.render(next(s for s in npv.scenarios if s["id"] == "oven"))
    assert oven.resolution == "VPL: R$ 9.140,40 (vale a pena)"
    assert "R$ 20.000,00, R$ 25.000,00 e R$ 30.000,00 nos anos 1, 2 e 3" in oven.question


def test_payback_must_be_whole_months() -> None:
    data = {
        "id": "x",
        "name": "X",
        "description": "X",
        "pairs_per_phase": 1,
        "phases": [
            {
                "id": "f1",
                "title": "F",
                "short_title": "F",
                "objective": "F",
                "calculator": "payback",
                "templates": {"default": {"question": "{investment}", "resolution": "{periods}", "explanation": "-"}},
                "scenarios": [{"id": "a", "investment": 1000, "gain": 300}],
            }
        ],
    }
    with pytest.raises(ContentError, match="meses inteiros"):
        parse_track(data)
