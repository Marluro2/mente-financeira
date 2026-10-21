"""Navegação entre as telas: abertura, Nível 1 (memória), Nível 2 (cálculos) e simulador."""

from __future__ import annotations

import random
from typing import Any, Protocol

import flet as ft

from mente_financeira.admin import admin_ativo
from mente_financeira.content import load_track
from mente_financeira.content.memory_deck import MemoryDeck, load_memory_deck
from mente_financeira.core.coin_challenge import COIN_KIT
from mente_financeira.core.engineering_challenge import ENGINEERING_KIT, ENGINEERING_LEVEL_KITS
from mente_financeira.core.medals import GameSummary, Medal, MedalBook
from mente_financeira.core.memory_game import MemoryGame, Mode
from mente_financeira.core.percent_challenge import PERCENT_KIT, ChallengeKit
from mente_financeira.core.session import GameSession
from mente_financeira.storage import SettingsStore
from mente_financeira import sugestoes
from mente_financeira.ui.admin_screen import AdminScreen
from mente_financeira.ui.app import DEFAULT_TRACK, MemoryFinanceApp
from mente_financeira.ui.factory_screen import FactoryScreen
from mente_financeira.ui.home import HomeScreen
from mente_financeira.ui.levels import Level, LevelsScreen, level_by_key
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui import style
from mente_financeira.ui.sounds import SoundEffects
from mente_financeira.ui.tracks import ENGENHARIA, FUNDAMENTAL, FUNDAMENTAL_1, TracksScreen


# Trilhas com jogo da memória: baralho (arquivo em content/) e Desafio Relâmpago
# do Duelo. As duas seguem a mesma lógica; muda só o conteúdo.
MEMORY_TRACKS = {
    FUNDAMENTAL_1: ("memoria_fundamental1", COIN_KIT),
    FUNDAMENTAL: ("memoria", PERCENT_KIT),
    ENGENHARIA: ("memoria_engenharia", ENGINEERING_KIT),
}

# Banco de questões do Nível 2 de cada trilha (as demais usam o do Ensino Médio).
LEVEL2_TRACKS = {ENGENHARIA: "engenharia"}


class Screen(Protocol):
    def stop(self) -> None: ...

    def on_resize(self, event: Any) -> None: ...


class GameShell:
    def __init__(
        self,
        page: ft.Page,
        *,
        store: SettingsStore | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.page = page
        self.store = store or SettingsStore()
        self.rng = rng or random.Random()
        self.track = FUNDAMENTAL
        self.level: str | None = None  # nível escolhido na Engenharia de Produção
        self.current: Screen | None = None
        # Efeitos sonoros compartilhados por todas as telas (carregados já na
        # abertura para o primeiro toque não atrasar).
        self.sounds = SoundEffects(page, self.store)
        self.sounds.preload()
        self.medals = MedalBook(self.store)  # conquistas, guardadas com as preferências
        style.apply_theme(self.store.load().theme)  # tema escolhido na página inicial
        self.page.title = "Mente Financeira"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.on_disconnect = self._stop_current
        self.show_tracks()

    @property
    def deck(self) -> MemoryDeck:
        """Baralho da trilha aberta; na Engenharia, só as cartas do nível escolhido."""

        deck = load_memory_deck(MEMORY_TRACKS[self.track][0])
        level = self._engineering_level()
        return deck.for_level(level.number) if level else deck

    def _engineering_level(self) -> Level | None:
        return level_by_key(self.level) if self.track == ENGENHARIA else None

    def _stop_current(self, _: Any = None) -> None:
        if self.current is not None:
            self.current.stop()

    def _activate(self, screen: Screen) -> None:
        self._stop_current()
        self.current = screen
        # Cada tela trata o redimensionamento do seu jeito.
        self.page.on_resize = screen.on_resize
        self.page.on_disconnect = self._stop_current

    def show_tracks(self) -> None:
        """Página inicial: escolha da trilha (Fundamental 1 e 2, Médio, Engenharia)."""

        tracks = TracksScreen(
            self.page,
            load_memory_deck(),
            on_select=self.open_track,
            rng=self.rng,
            suggest_url=sugestoes.FORM_URL or None,
            on_theme=self.choose_theme,
        )
        self._activate(tracks)
        tracks.show()

    def choose_theme(self, key: str) -> None:
        """Troca o tema de cores, guarda a escolha e redesenha a página inicial."""

        theme = style.apply_theme(key)
        settings = self.store.load()
        settings.theme = theme.key
        self.store.save(settings)
        if isinstance(self.current, TracksScreen):
            self.current.show()  # redesenha com as novas cores, seletor ainda aberto
        else:
            self.show_tracks()

    def open_track(self, key: str) -> None:
        # Só as trilhas com jogo da memória abrem; o Ensino Médio aparece como
        # "Em breve" na página inicial.
        if key in MEMORY_TRACKS:
            self.track = key
            if key == ENGENHARIA:
                self.show_levels()  # a Engenharia escolhe o nível antes do modo de jogo
            else:
                self.show_home()

    def show_levels(self) -> None:
        """Escolha do nível da Engenharia de Produção (todos abertos)."""

        levels = LevelsScreen(self.page, on_select=self.choose_level, on_tracks=self.show_tracks, rng=self.rng)
        self._activate(levels)
        levels.show()

    def choose_level(self, key: str) -> None:
        # Cada nível tem o seu Desafio Relâmpago (content/banco_engenharia.toml).
        self.level = key
        self.show_home()

    def show_home(self) -> None:
        """Abertura da trilha aberta (Ensino Fundamental 1 ou 2, Engenharia)."""

        engineering = self.track == ENGENHARIA
        level = self._engineering_level()
        home = HomeScreen(
            self.page,
            self.deck,
            on_play=self.play_memory,
            on_level2=self.open_level2,
            # O painel do professor traz as questões do Ensino Fundamental 2.
            on_admin=self.open_admin if admin_ativo() and self.track == FUNDAMENTAL else None,
            # Na Engenharia, voltar leva à escolha do nível.
            on_tracks=self.show_levels if engineering else self.show_tracks,
            back_label="Níveis" if engineering else "Trilhas",
            level_label=f"Nível {level.number} • {level.title}" if level else None,
            medals=self.medals,
            on_factory=self.open_factory if engineering else None,
        )
        self._activate(home)
        home.show()

    def open_admin(self) -> None:
        panel = AdminScreen(self.page, self.deck, load_track(DEFAULT_TRACK), on_home=self.show_home, rng=self.rng)
        self._activate(panel)
        panel.show()

    def play_memory(self, mode: Mode, names: tuple[str | None, str | None]) -> None:
        game = MemoryGame(self.deck, self.rng)
        game.new_game(mode, names)
        level = self._engineering_level()
        screen = MemoryScreen(
            self.page,
            game,
            on_home=self.show_home,
            on_level2=self.open_level2,
            sounds=self.sounds,
            challenges=self._challenges(),
            medals=self._record_medals,
            level_number=level.number if level else 1,
        )
        self._activate(screen)
        screen.show()

    def _challenges(self) -> ChallengeKit:
        """Desafio Relâmpago da trilha; na Engenharia, o do nível escolhido."""

        level = self._engineering_level()
        return ENGINEERING_LEVEL_KITS[level.number] if level else MEMORY_TRACKS[self.track][1]

    def _record_medals(self, game: MemoryGame, right_labels: set[str]) -> list[Medal]:
        return self.medals.record(GameSummary.of(game, self.track, right_labels))

    def open_factory(self) -> None:
        """Simulador "Minha fábrica": comprar, alugar ou financiar uma máquina."""

        factory = FactoryScreen(self.page, on_home=self.show_home, sounds=self.sounds)
        self._activate(factory)
        factory.show()

    def open_level2(self) -> None:
        self._stop_current()
        session = GameSession(load_track(LEVEL2_TRACKS.get(self.track, DEFAULT_TRACK)))
        level2 = MemoryFinanceApp(
            self.page, session=session, store=self.store, on_home=self.show_home, sounds=self.sounds
        )
        self._activate(level2)
