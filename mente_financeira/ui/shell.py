"""Navegação entre as telas: abertura, Nível 1 (memória) e Nível 2 (cálculos)."""

from __future__ import annotations

import random
from typing import Any, Protocol

import flet as ft

from mente_financeira.admin import admin_ativo
from mente_financeira.content import load_track
from mente_financeira.content.memory_deck import MemoryDeck, load_memory_deck
from mente_financeira.core.coin_challenge import COIN_KIT
from mente_financeira.core.memory_game import MemoryGame, Mode
from mente_financeira.core.percent_challenge import PERCENT_KIT
from mente_financeira.storage import SettingsStore
from mente_financeira import sugestoes
from mente_financeira.ui.admin_screen import AdminScreen
from mente_financeira.ui.app import DEFAULT_TRACK, MemoryFinanceApp
from mente_financeira.ui.home import HomeScreen
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.sounds import SoundEffects
from mente_financeira.ui.tracks import FUNDAMENTAL, FUNDAMENTAL_1, TracksScreen


# Trilhas com jogo da memória: baralho (arquivo em content/) e Desafio Relâmpago
# do Duelo. As duas seguem a mesma lógica; muda só o conteúdo.
MEMORY_TRACKS = {
    FUNDAMENTAL_1: ("memoria_fundamental1", COIN_KIT),
    FUNDAMENTAL: ("memoria", PERCENT_KIT),
}


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
        self.current: Screen | None = None
        # Efeitos sonoros compartilhados por todas as telas (carregados já na
        # abertura para o primeiro toque não atrasar).
        self.sounds = SoundEffects(page, self.store)
        self.sounds.preload()
        self.page.title = "Mente Financeira"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.on_disconnect = self._stop_current
        self.show_tracks()

    @property
    def deck(self) -> MemoryDeck:
        """Baralho da trilha aberta."""

        return load_memory_deck(MEMORY_TRACKS[self.track][0])

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
            on_suggest=self.open_suggestion_form if sugestoes.FORM_URL else None,
        )
        self._activate(tracks)
        tracks.show()

    def open_suggestion_form(self) -> None:
        """Abre o Formulário Google de sugestões em outra aba."""

        self.page.run_task(self.page.launch_url, sugestoes.FORM_URL)

    def open_track(self, key: str) -> None:
        # Por enquanto só os Ensinos Fundamentais 1 e 2 estão disponíveis; as
        # demais trilhas aparecem como "Em breve" na página inicial.
        if key in MEMORY_TRACKS:
            self.track = key
            self.show_home()

    def show_home(self) -> None:
        """Abertura da trilha aberta (Ensino Fundamental 1 ou 2)."""

        home = HomeScreen(
            self.page,
            self.deck,
            on_play=self.play_memory,
            on_level2=self.open_level2,
            # O painel do professor traz as questões do Ensino Fundamental 2.
            on_admin=self.open_admin if admin_ativo() and self.track == FUNDAMENTAL else None,
            on_tracks=self.show_tracks,
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
        screen = MemoryScreen(
            self.page,
            game,
            on_home=self.show_home,
            on_level2=self.open_level2,
            sounds=self.sounds,
            challenges=MEMORY_TRACKS[self.track][1],
        )
        self._activate(screen)
        screen.show()

    def open_level2(self) -> None:
        self._stop_current()
        level2 = MemoryFinanceApp(self.page, store=self.store, on_home=self.show_home, sounds=self.sounds)
        self._activate(level2)
