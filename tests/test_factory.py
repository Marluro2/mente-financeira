"""Simulador "Minha fábrica": contas de cada caminho e a tela da Engenharia."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import random
from types import SimpleNamespace

import flet as ft
import pytest

from fakes import FakePage, walk
from mente_financeira.core.factory import (
    MACHINES,
    Choice,
    best_choice,
    signed_money,
    simulate,
    verdict,
)
from mente_financeira.finance import net_present_value, price_payment, round_money
from mente_financeira.storage import SettingsStore
from mente_financeira.ui.factory_screen import FactoryScreen
from mente_financeira.ui.home import HomeScreen
from mente_financeira.ui.shell import GameShell
from mente_financeira.ui.tracks import ENGENHARIA, FUNDAMENTAL, FUNDAMENTAL_1

PACKER = MACHINES[0]  # máquina de embalar: R$ 60.000, caixa de R$ 80.000


# ====================================================================== contas
def test_buying_pays_everything_today_and_resells_at_the_end() -> None:
    plan = simulate(PACKER)[Choice.BUY]
    assert plan.flows == (-60_000, 18_000, 18_000, 18_000, 18_000, 28_000)
    assert plan.npv == round_money(net_present_value(60_000, [18_000] * 4 + [28_000], "0.10")) == Decimal("14443.38")
    assert plan.balances == (20_000, 38_000, 56_000, 74_000, 92_000, 120_000)  # caixa de R$ 80.000 menos a máquina
    assert plan.fits and plan.lowest == 20_000 and plan.lowest_year == 0


def test_renting_has_no_down_payment_and_no_resale() -> None:
    plan = simulate(PACKER)[Choice.RENT]
    assert plan.payment == 15_000
    assert plan.flows == (0, 3_000, 3_000, 3_000, 3_000, 3_000)
    assert plan.balances[0] == PACKER.cash


def test_financing_pays_a_down_payment_and_price_installments() -> None:
    plan = simulate(PACKER)[Choice.FINANCE]
    installment = round_money(price_payment(48_000, "0.12", 5))  # 80% de R$ 60.000 a 12% ao ano
    assert plan.payment == installment == Decimal("13315.67")
    assert plan.flows[0] == -12_000 and plan.flows[1] == 18_000 - installment
    assert plan.flows[-1] == 18_000 - installment + 10_000  # última parcela e a revenda


def test_each_machine_teaches_a_different_answer() -> None:
    answers = [best_choice(simulate(machine)) for machine in MACHINES]
    assert answers == [Choice.BUY, Choice.FINANCE, Choice.RENT, Choice.FINANCE]


def test_the_best_choice_must_fit_in_the_cash() -> None:
    robot = MACHINES[1]
    plans = simulate(robot)
    assert not plans[Choice.BUY].fits  # R$ 150.000 com R$ 60.000 em caixa
    assert plans[Choice.BUY].lowest == -90_000
    # Mesmo que comprar tivesse o maior VPL, ficaria de fora por falta de caixa.
    assert best_choice({Choice.BUY: plans[Choice.BUY]}) is Choice.BUY  # sem alternativa, fica o maior VPL
    rich = simulate(robot, tma=Decimal("0.01"), loan_rate=Decimal("0.30"))
    assert rich[Choice.BUY].npv > rich[Choice.FINANCE].npv and best_choice(rich) is not Choice.BUY


def test_cheap_loans_make_financing_the_best_choice() -> None:
    assert best_choice(simulate(PACKER)) is Choice.BUY  # juros de 12% > TMA de 10%
    plans = simulate(PACKER, tma=Decimal("0.15"), loan_rate=Decimal("0.05"))
    assert best_choice(plans) is Choice.FINANCE
    assert "menores que a TMA" in verdict(PACKER, plans, Choice.FINANCE, tma=Decimal("0.15"), loan_rate=Decimal("0.05"))


def test_zero_rates_still_work() -> None:
    plans = simulate(PACKER, tma=0, loan_rate=0)
    assert plans[Choice.FINANCE].payment == 9_600  # R$ 48.000 em 5 parcelas sem juros
    assert plans[Choice.BUY].npv == sum(plans[Choice.BUY].flows)


def test_verdicts_explain_right_short_of_cash_and_worse_choices() -> None:
    robot = MACHINES[1]
    plans = simulate(robot)
    rates = {"tma": robot.tma, "loan_rate": robot.loan_rate}
    assert verdict(robot, plans, Choice.FINANCE, **rates).startswith("Boa escolha! Financiar tem o maior VPL (R$ 40.897)")
    assert verdict(robot, plans, Choice.BUY, **rates).startswith("Faltaria dinheiro: com essa escolha o caixa chega a −R$ 90.000 no ano 0.")
    assert verdict(robot, plans, Choice.RENT, **rates).startswith("Dá para pagar, mas financiar vale R$ 8.454 a mais em VPL")
    truck = MACHINES[2]
    assert "VPL negativo" in verdict(truck, simulate(truck), Choice.BUY, tma=truck.tma, loan_rate=truck.loan_rate)


def test_money_without_cents_and_with_a_real_minus_sign() -> None:
    assert signed_money(Decimal("14443.38")) == "R$ 14.443"
    assert signed_money(Decimal("-90000")) == "−R$ 90.000"
    assert signed_money(Decimal("0")) == "R$ 0"


# ====================================================================== tela
PHONE, NOTEBOOK = (360, 740), (1366, 768)


@pytest.fixture(params=[PHONE, NOTEBOOK], ids=["celular", "notebook"])
def shell(request: pytest.FixtureRequest, tmp_path: Path) -> GameShell:
    shell = GameShell(FakePage(*request.param), store=SettingsStore(tmp_path), rng=random.Random(3))  # type: ignore[arg-type]
    shell.open_track(ENGENHARIA)
    shell.choose_level("nivel1")  # a Engenharia passa pela escolha do nível
    return shell


def _texts(control: ft.Control) -> list[str]:
    texts = []
    for c in walk(control):
        if isinstance(c, ft.Text):
            texts.append(c.value if isinstance(c.value, str) else "".join(span.text for span in c.spans or []))
    return texts


def _pick(screen: FactoryScreen, choice: Choice) -> None:
    screen._pick(SimpleNamespace(control=SimpleNamespace(data=choice)))


def test_only_engineering_has_the_factory_card(shell: GameShell) -> None:
    assert "Minha fábrica" in _texts(shell.page.controls[-1])
    for track in (FUNDAMENTAL_1, FUNDAMENTAL):
        shell.show_tracks()
        shell.open_track(track)
        assert isinstance(shell.current, HomeScreen) and shell.current.on_factory is None
        assert "Minha fábrica" not in _texts(shell.page.controls[-1])


def test_choosing_reveals_npv_cash_and_the_verdict(shell: GameShell) -> None:
    shell.current._open_factory()  # type: ignore[union-attr]
    screen = shell.current
    assert isinstance(screen, FactoryScreen)
    before = _texts(shell.page.controls[-1])
    assert "Escolher" in before and "R$ 14.443" not in before  # o VPL só aparece depois da escolha
    _pick(screen, Choice.RENT)
    after = _texts(shell.page.controls[-1])
    assert {"R$ 14.443", "R$ 11.372", "R$ 11.967"} <= set(after)  # VPL dos três caminhos
    assert "Acertos: 0 de 1" in after and "Melhor escolha" in after and "Sua escolha" in after
    assert any(text.startswith("Dá para pagar, mas comprar à vista vale R$ 3.071 a mais") for text in after)
    assert "Caixa da fábrica ano a ano" in after
    _pick(screen, Choice.BUY)  # depois de escolher, não troca
    assert screen.picked is Choice.RENT and screen.played == 1


def test_what_if_rates_change_the_best_choice(shell: GameShell) -> None:
    shell.open_factory()
    screen: FactoryScreen = shell.current  # type: ignore[assignment]
    _pick(screen, Choice.BUY)
    assert screen.right == 1
    screen._change_loan(SimpleNamespace(control=SimpleNamespace(value=5.0)))
    screen._change_tma(SimpleNamespace(control=SimpleNamespace(value=15.0)))
    assert (screen.tma, screen.loan_rate) == (Decimal("0.15"), Decimal("0.05"))
    texts = _texts(shell.page.controls[-1])
    assert "TMA da fábrica: 15% ao ano" in texts and "Juros do banco: 5% ao ano" in texts
    assert any("menores que a TMA" in text for text in texts)
    screen._restore_rates()
    assert (screen.tma, screen.loan_rate) == (PACKER.tma, PACKER.loan_rate)
    assert screen.right == 1  # mexer nas taxas não muda o placar


def test_next_machine_and_back_to_the_track(shell: GameShell) -> None:
    shell.open_factory()
    screen: FactoryScreen = shell.current  # type: ignore[assignment]
    for machine in [*MACHINES[1:], MACHINES[0]]:
        _pick(screen, best_choice(simulate(screen.machine)))
        screen._next()
        assert screen.machine is machine and screen.picked is None
    assert (screen.right, screen.played) == (len(MACHINES), len(MACHINES))
    screen.on_home()
    assert isinstance(shell.current, HomeScreen)


def test_factory_layout_switches_with_the_window(shell: GameShell) -> None:
    shell.open_factory()
    screen: FactoryScreen = shell.current  # type: ignore[assignment]
    _pick(screen, Choice.FINANCE)
    page: FakePage = shell.page  # type: ignore[assignment]
    page.resize(*(NOTEBOOK if screen.compact else PHONE))
    assert screen.compact is (page.width == PHONE[0])
    offenders = [
        child
        for control in walk(page.controls[-1])
        if isinstance(control, ft.Row) and control.wrap
        for child in control.controls
        if child.expand
    ]
    assert offenders == []
