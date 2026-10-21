"""Página inicial: escolha da trilha (Fundamental 1 e 2, Médio, Engenharia de Produção)."""

import asyncio
from pathlib import Path
import random
from types import SimpleNamespace

import flet as ft
import pytest

from fakes import FakePage, walk
from mente_financeira.core.coin_challenge import COIN_KIT
from mente_financeira.core.engineering_challenge import ENGINEERING_LEVEL_KITS
from mente_financeira.core.memory_game import Mode
from mente_financeira.storage import SettingsStore
from mente_financeira.ui import style
from mente_financeira.ui import tracks as tracks_module
from mente_financeira.ui.home import HomeScreen
from mente_financeira.ui.levels import LevelsScreen
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.shell import GameShell
from mente_financeira.ui.suggestion_form import SUGGESTION_QR
from mente_financeira.ui.tracks import ENGENHARIA, FUNDAMENTAL, FUNDAMENTAL_1, MEDIO, TRACKS, TracksScreen

PHONE, NOTEBOOK, DESKTOP = (360, 740), (1536, 785), (1920, 1000)


@pytest.fixture(autouse=True)
def default_theme():
    """As cores ficam no módulo de estilo: cada teste termina no tema padrão."""

    yield
    style.apply_theme(style.DEFAULT_THEME)


@pytest.fixture(params=[PHONE, NOTEBOOK, DESKTOP], ids=["celular", "notebook", "computador"])
def shell(request: pytest.FixtureRequest, tmp_path: Path) -> GameShell:
    return GameShell(FakePage(*request.param), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]


def _texts(control: ft.Control) -> list[str]:
    return [c.value for c in walk(control) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def _click(screen: TracksScreen, key: str) -> None:
    screen._choose(SimpleNamespace(control=SimpleNamespace(data=key)))


def test_game_opens_on_the_tracks_page(shell: GameShell) -> None:
    assert isinstance(shell.current, TracksScreen)
    texts = _texts(shell.page.controls[-1])
    for title in ("Ensino Fundamental 1", "Ensino Fundamental 2", "Ensino Médio", "Engenharia de Produção", "Qual é a sua trilha?"):
        assert title in texts
    assert texts.count("EM BREVE") == 1  # só o Ensino Médio
    assert [t.key for t in TRACKS] == [FUNDAMENTAL_1, FUNDAMENTAL, MEDIO, ENGENHARIA]  # ordem dos botões


def test_fundamental_opens_the_current_game_and_can_come_back(shell: GameShell) -> None:
    _click(shell.current, FUNDAMENTAL)
    home = shell.current
    assert isinstance(home, HomeScreen)
    texts = _texts(shell.page.controls[-1])
    assert "Como você quer jogar?" in texts and "Desafio dos Cálculos" not in texts
    back = next(c for c in walk(shell.page.controls[-1]) if isinstance(c, ft.TextButton) and c.content == "Trilhas")
    back.on_click(None)
    assert isinstance(shell.current, TracksScreen)
    assert shell.page.on_resize == shell.current.on_resize


def test_fundamental1_opens_its_own_memory_game(shell: GameShell) -> None:
    _click(shell.current, FUNDAMENTAL_1)
    assert isinstance(shell.current, HomeScreen)
    assert shell.deck.concepts[0].id == "dinheiro"  # baralho do Ensino Fundamental 1
    shell.play_memory(Mode.DUEL, ("Ana", "Bruno"))
    screen: MemoryScreen = shell.current  # type: ignore[assignment]
    assert {c.id for c in screen.game.cards} <= {c.id for c in shell.deck.concepts}
    assert screen.challenges is COIN_KIT  # desafio de contas, sem porcentagem
    # Voltar às trilhas e entrar no Fundamental 2 troca o baralho.
    shell.show_tracks()
    _click(shell.current, FUNDAMENTAL)
    assert shell.deck.concepts[0].id == "poupanca"


def test_engineering_opens_its_own_game_and_level2(shell: GameShell) -> None:
    _click(shell.current, ENGENHARIA)
    assert isinstance(shell.current, LevelsScreen)  # antes do jogo, a escolha do nível
    shell.current._choose(SimpleNamespace(control=SimpleNamespace(data="nivel1")))
    assert isinstance(shell.current, HomeScreen)
    assert shell.deck.concepts[0].id == "fluxo_caixa"  # baralho de engenharia econômica
    shell.play_memory(Mode.DUEL, ("Ana", "Bruno"))
    screen: MemoryScreen = shell.current  # type: ignore[assignment]
    assert {c.id for c in screen.game.cards} <= {c.id for c in shell.deck.concepts}
    assert screen.challenges is ENGINEERING_LEVEL_KITS[1]  # questões do Nível 1
    shell.open_level2()
    assert shell.current.session.track.id == "engenharia"  # type: ignore[attr-defined]
    # As outras trilhas continuam com o Nível 2 do Ensino Médio.
    shell.show_tracks()
    _click(shell.current, FUNDAMENTAL)
    shell.open_level2()
    assert shell.current.session.track.id == "medio"  # type: ignore[attr-defined]


def test_medio_only_announces_coming_soon(shell: GameShell) -> None:
    screen = shell.current
    _click(screen, MEDIO)
    assert shell.current is screen  # continua na página inicial
    assert "em construção" in shell.page.dialogs[-1].content.value


def test_board_uses_the_card_back_and_fits_the_window(shell: GameShell) -> None:
    screen: TracksScreen = shell.current  # type: ignore[assignment]
    page = shell.page
    # Fora do tabuleiro só há o QR code do formulário de sugestões.
    images = [c.src for c in walk(page.controls[-1]) if isinstance(c, ft.Image) and c.src != SUGGESTION_QR]
    assert images and set(images) == {screen.deck.back_image}
    board_width = 4 * screen.card_size + 3 * (8 if screen.compact else 12)
    assert board_width <= page.width
    assert len(screen.switchers) == (8 if screen.compact else 16)
    if not screen.compact:
        assert board_width + 480 + 64 <= page.width  # botões + tabuleiro lado a lado
        assert board_width <= page.height


def test_cards_flip_one_at_a_time_and_stop_when_leaving(shell: GameShell, monkeypatch: pytest.MonkeyPatch) -> None:
    screen: TracksScreen = shell.current  # type: ignore[assignment]
    monkeypatch.setattr(tracks_module, "FLIP_PERIOD_SECONDS", 0)
    generation = screen.generation

    async def run_three_flips() -> None:
        task = asyncio.ensure_future(screen._flip_loop(generation))
        for _ in range(40):
            await asyncio.sleep(0)
        screen.stop()
        await task

    asyncio.run(run_three_flips())
    fronts = [sw for sw in screen.switchers if sw.content.src != screen.deck.back_image]
    assert len(fronts) <= 1  # no máximo uma carta aberta por vez
    assert screen.generation != generation


def test_no_expanded_child_inside_wrapping_row(shell: GameShell) -> None:
    offenders = [
        child
        for control in walk(shell.page.controls[-1])
        if isinstance(control, ft.Row) and control.wrap
        for child in control.controls
        if child.expand
    ]
    assert offenders == []


# ====================================================================== cores
def _theme_button(page: FakePage) -> ft.Container:
    return next(c for c in walk(page.controls[-1]) if isinstance(c, ft.Container) and c.tooltip == "Escolher as cores")


def _swatches(page: FakePage) -> list[ft.Container]:
    keys = {theme.key for theme in style.THEMES}
    return [c for c in walk(page.controls[-1]) if isinstance(c, ft.Container) and c.data in keys]


def test_color_picker_opens_with_the_five_themes(shell: GameShell) -> None:
    assert _swatches(shell.page) == []  # fechado ao abrir o jogo
    _theme_button(shell.page).on_click(None)
    assert [c.data for c in _swatches(shell.page)] == ["neon", "oceano", "floresta", "por_do_sol", "grafite"]
    texts = _texts(shell.page.controls[-1])
    assert "Escolha as cores da tela e das caixinhas" in texts
    assert {"Roxo Neon", "Oceano", "Floresta", "Pôr do Sol", "Grafite"} <= set(texts)
    _theme_button(shell.page).on_click(None)
    assert _swatches(shell.page) == []


def test_choosing_a_theme_recolors_screen_and_cards_and_is_remembered(shell: GameShell, tmp_path: Path) -> None:
    screen: TracksScreen = shell.current  # type: ignore[assignment]
    assert screen.switchers[0].content.src == "cartas/verso.svg"
    _theme_button(shell.page).on_click(None)
    oceano = next(c for c in _swatches(shell.page) if c.data == "oceano")
    oceano.on_click(SimpleNamespace(control=oceano))

    assert shell.current is screen and screen.picker_open  # continua aberto para comparar
    assert shell.page.bgcolor == "#04122B"
    assert screen.switchers[0].content.src == "cartas/temas/verso_oceano.svg"
    assert (tmp_path / "settings.json").exists() and SettingsStore(tmp_path).load().theme == "oceano"
    assert (Path("assets") / "cartas/temas/verso_oceano.svg").is_file()

    # Ao abrir o jogo de novo, o tema volta; e vale nas outras telas.
    style.apply_theme(style.DEFAULT_THEME)
    again = GameShell(FakePage(*PHONE), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    assert again.page.bgcolor == "#04122B"
    _click(again.current, FUNDAMENTAL)
    assert again.page.bgcolor == "#04122B"
    again.play_memory(Mode.SOLO, ("Ana", None))
    memory: MemoryScreen = again.current  # type: ignore[assignment]
    backs = [c for c in walk(again.page.controls[-1]) if isinstance(c, ft.Image) and c.semantics_label == "Carta virada"]
    assert backs and all(b.src == "cartas/temas/verso_oceano.svg" for b in backs)
    assert isinstance(memory, MemoryScreen)


def test_every_theme_has_its_card_back_file() -> None:
    for theme in style.THEMES:
        assert (Path("assets") / theme.card_back).is_file(), theme.key


def test_unknown_saved_theme_falls_back_to_the_default(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path)
    settings = store.load()
    settings.theme = "arco-iris"
    store.save(settings)
    GameShell(FakePage(*PHONE), store=store, rng=random.Random(2))  # type: ignore[arg-type]
    assert style.theme_key == style.DEFAULT_THEME and style.BG_TOP == "#12082E"
