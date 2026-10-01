"""Telas do jogo em Flet.

Esta camada só desenha e reage a toques. Regras da partida ficam em
``mente_financeira.core``; conteúdo em ``mente_financeira.content``.

A interface se adapta a três faixas de largura (``ui.layout``): celular
(compacta), tablet (média) e computador (larga).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import Future
from typing import Any

import flet as ft

from mente_financeira.admin import admin_ativo
from mente_financeira.content import load_track
from mente_financeira.core import QUESTION, RESOLUTION, GameSession, Selection
from mente_financeira.storage import Settings, SettingsStore
from mente_financeira.ui import style as s
from mente_financeira.ui.layout import METRICS, Layout, Metrics, layout_for
from mente_financeira.ui.sounds import SoundEffects
from mente_financeira.ui.theme import DEFAULT_PALETTE, PALETTES, Palette
from mente_financeira.ui.whiteboard import Whiteboard

DEFAULT_TRACK = "medio"
REVEAL_DELAY_SECONDS = 0.9
TIMER_WARNING_SECONDS = 15
START_CARD_MAX_WIDTH = 820
SIDE_WHITEBOARD_WIDTH = 330

START_SCREEN = "start"
GAME_SCREEN = "game"


class MemoryFinanceApp:
    def __init__(
        self,
        page: ft.Page,
        *,
        session: GameSession | None = None,
        store: SettingsStore | None = None,
        on_home: Callable[[], None] | None = None,
        sounds: SoundEffects | None = None,
    ) -> None:
        self.page = page
        self.on_home = on_home  # volta à abertura do jogo (Nível 2 dentro do menu)
        self.admin = admin_ativo()  # modo administrador: sem cronômetro
        self.session = session or GameSession(load_track(DEFAULT_TRACK))
        self.store = store or SettingsStore()
        self.sounds = sounds or SoundEffects(page, self.store)
        settings = self.store.load()
        self.palette_key = settings.palette if settings.palette in PALETTES else DEFAULT_PALETTE
        self.dark_mode = settings.dark_mode
        self.layout = layout_for(page.width)
        self.screen = START_SCREEN
        # Invalida tarefas assíncronas (cronômetro, atraso de revelação) de
        # fases anteriores sempre que uma nova fase ou tela é iniciada.
        self.phase_generation = 0
        self.timer_future: Future[None] | None = None
        self.whiteboard: Whiteboard | None = None
        self.whiteboard_sheet: ft.BottomSheet | None = None
        self.whiteboard_visible = False

        self.name_1: ft.TextField | None = None
        self.name_2: ft.TextField | None = None
        self.turn_text: ft.Text
        self.score_text: ft.Text
        self.timer_text: ft.Text
        self.timer_progress: ft.ProgressBar
        self.overall_progress: ft.ProgressBar
        self.left_cards: ft.Column
        self.right_cards: ft.Column
        self.focus_text: ft.Text
        self.focus_box: ft.Container
        self.advance_button: ft.Button
        self.whiteboard_button: ft.Control
        self.game_body: ft.Row

        self._configure_page()
        self._show_start_screen()

    # ------------------------------------------------------------- cores
    @property
    def palette(self) -> Palette:
        return PALETTES[self.palette_key]

    @property
    def metrics(self) -> Metrics:
        return METRICS[self.layout]

    @property
    def compact(self) -> bool:
        return self.layout is Layout.COMPACT

    @property
    def background(self) -> str:
        return self.palette.dark_background if self.dark_mode else self.palette.light_background

    @property
    def surface(self) -> str:
        return self.palette.dark_surface if self.dark_mode else self.palette.light_surface

    @property
    def text_color(self) -> str:
        return "#F7F3FA" if self.dark_mode else "#211D25"

    @property
    def muted_color(self) -> str:
        return "#C9C3D6" if self.dark_mode else "#625C6B"

    @property
    def border_color(self) -> str:
        return "#473E5E" if self.dark_mode else "#E4E0EA"

    def _apply_theme(self, *, dark: bool) -> None:
        self.page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed=self.palette.primary, use_material3=True)
        self.page.dark_theme = ft.Theme(color_scheme_seed=self.palette.primary, use_material3=True)
        self.page.bgcolor = self.palette.dark_background if dark else self.palette.light_background

    def _save_settings(self) -> None:
        # Parte das preferências atuais para não apagar as demais (ex.: som).
        settings = self.store.load()
        settings.palette, settings.dark_mode = self.palette_key, self.dark_mode
        self.store.save(settings)

    # ------------------------------------------------------------- página
    def _configure_page(self) -> None:
        self.page.title = "Mente Financeira — Memória de Porcentagens"
        self.page.padding = 0
        self.page.spacing = 0
        self._apply_theme(dark=self.dark_mode)
        self.page.on_disconnect = self._stop_background_tasks
        self.page.on_resize = self._on_resize

    def _on_resize(self, event: Any) -> None:
        new_layout = layout_for(getattr(event, "width", None) or self.page.width)
        if new_layout is self.layout:
            return
        self.layout = new_layout
        if self.screen == GAME_SCREEN:
            self._rebuild_game_screen()
        else:
            self._show_start_screen(stop_tasks=False)

    # Interface usada pela navegação (ui.shell).
    def stop(self) -> None:
        self._stop_background_tasks()

    def on_resize(self, event: Any) -> None:
        self._on_resize(event)

    def _stop_background_tasks(self, _: Any = None) -> None:
        self.phase_generation += 1
        self.session.stop()
        if self.timer_future and not self.timer_future.done():
            self.timer_future.cancel()

    def _set_root(self, control: ft.Control) -> None:
        self.page.controls.clear()
        # SafeArea evita que o conteúdo fique sob o entalhe e as barras do celular.
        self.page.add(ft.SafeArea(content=control, expand=True))

    def _primary_button(
        self,
        label: str,
        icon: ft.IconData,
        on_click: Any,
        *,
        visible: bool = True,
        height: int = 48,
    ) -> ft.Button:
        return ft.Button(
            label,
            icon=icon,
            on_click=on_click,
            visible=visible,
            height=height,
            style=ft.ButtonStyle(
                bgcolor=self.palette.primary,
                color=self.palette.on_primary,
                padding=14,
                shape=ft.RoundedRectangleBorder(radius=14),
            ),
        )

    def _outline_button(self, label: str, icon: ft.IconData, on_click: Any) -> ft.Control:
        if self.metrics.icon_only_actions:
            return ft.IconButton(
                icon,
                tooltip=label,
                on_click=on_click,
                icon_color=self.palette.primary,
                style=ft.ButtonStyle(side=ft.BorderSide(1.5, self.palette.primary)),
            )
        return ft.OutlinedButton(
            label,
            icon=icon,
            on_click=on_click,
            height=46,
            style=ft.ButtonStyle(
                color=self.palette.primary,
                side=ft.BorderSide(1.5, self.palette.primary),
                padding=12,
                shape=ft.RoundedRectangleBorder(radius=14),
            ),
        )

    # ---------------------------------------------------------- tela inicial
    def _show_start_screen(self, *, stop_tasks: bool = True) -> None:
        if stop_tasks:
            self._stop_background_tasks()
        self.screen = START_SCREEN
        # A tela inicial tem cores próprias (claras); o modo escuro escolhido
        # é preservado e volta a valer no tabuleiro.
        self._apply_theme(dark=False)
        compact = self.compact
        # Preserva o que já foi digitado quando a tela é redesenhada.
        typed = [field.value if field else None for field in (self.name_1, self.name_2)]

        self.name_1 = ft.TextField(
            value=typed[0],
            label="Nome do Jogador 1",
            hint_text="Ex.: Ana",
            prefix_icon=ft.Icons.PERSON,
            border_radius=14,
            col={"xs": 12, "md": 6},
            max_length=24,
            autofocus=not compact,  # no celular, não abre o teclado sozinho
        )
        self.name_2 = ft.TextField(
            value=typed[1],
            label="Nome do Jogador 2",
            hint_text="Ex.: Bruno",
            prefix_icon=ft.Icons.PERSON,
            border_radius=14,
            col={"xs": 12, "md": 6},
            max_length=24,
            on_submit=self._prepare_players,
        )

        instructions = ft.ResponsiveRow(
            [
                self._instruction_card("1", "Vire uma questão", "Comece sempre pelo lado esquerdo.", ft.Icons.HELP_OUTLINE),
                self._instruction_card("2", "Procure a resolução", "Escolha uma carta do lado direito.", ft.Icons.CALCULATE),
                self._instruction_card("3", "Aprenda com o par", "Quem acerta pontua e joga novamente.", ft.Icons.LIGHTBULB),
            ],
            spacing=12,
            run_spacing=12,
        )

        page_width = self.page.width or START_CARD_MAX_WIDTH
        content = ft.Container(
            width=min(START_CARD_MAX_WIDTH, max(280, page_width - 24)),
            padding=ft.Padding.symmetric(horizontal=18 if compact else 28, vertical=20 if compact else 30),
            bgcolor="#FFFFFF",
            border_radius=22 if compact else 28,
            shadow=ft.BoxShadow(blur_radius=30, color="#240F0A2A", offset=ft.Offset(0, 12)),
            content=ft.Column(
                [
                    *(
                        [
                            ft.Row(
                                [
                                    ft.TextButton(
                                        "Menu inicial",
                                        icon=ft.Icons.ARROW_BACK_ROUNDED,
                                        on_click=lambda _: self.on_home(),
                                        style=ft.ButtonStyle(color=self.palette.primary),
                                    )
                                ]
                            )
                        ]
                        if self.on_home
                        else []
                    ),
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                        bgcolor="#EFEAFF",
                        border_radius=20,
                        content=ft.Text(
                            "NÍVEL 2 • DESAFIO DOS CÁLCULOS" if self.on_home else "PROJETO DE INICIAÇÃO CIENTÍFICA",
                            size=10 if compact else 11,
                            weight=ft.FontWeight.BOLD,
                            color=self.palette.primary,
                        ),
                    ),
                    ft.Row(
                        [
                            ft.Container(
                                width=48 if compact else 62,
                                height=48 if compact else 62,
                                border_radius=16 if compact else 20,
                                bgcolor=self.palette.primary,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.MEMORY, color="#FFFFFF", size=26 if compact else 34),
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Mente Financeira",
                                        size=26 if compact else 36,
                                        weight=ft.FontWeight.BOLD,
                                        color="#211D25",
                                    ),
                                    ft.Text(
                                        "Porcentagem na ponta dos dedos",
                                        size=14 if compact else 18,
                                        color=self.palette.primary,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                        ],
                        # Sem wrap: no Flutter, um filho com expand dentro de
                        # uma linha com quebra gera erro (bloco cinza).
                    ),
                    ft.Text(
                        "Um laboratório divertido para dominar porcentagens, juros, inflação e financiamentos no dia a dia.",
                        size=14 if compact else 15,
                        color="#625C6B",
                    ),
                    ft.Divider(color="#ECE8F0"),
                    ft.Text("Quem vai jogar?", size=20 if compact else 22, weight=ft.FontWeight.BOLD, color="#211D25"),
                    ft.ResponsiveRow([self.name_1, self.name_2], spacing=12, run_spacing=12),
                    self._primary_button("Continuar", ft.Icons.ARROW_FORWARD, self._prepare_players),
                    ft.Divider(color="#ECE8F0"),
                    instructions,
                    ft.Text(
                        f"{self.session.phase_count} fases • {self.session.track.pairs_per_phase} pares por fase • lousa de cálculo incluída",
                        size=12,
                        color="#817A88",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=14 if compact else 18,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )

        root = ft.Container(
            expand=True,
            padding=12 if compact else 20,
            alignment=ft.Alignment.CENTER,
            gradient=ft.LinearGradient(colors=["#FFF4D6", "#EEE9FF", "#E6FAF6"]),
            content=ft.Column(
                [content],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
        self._set_root(root)

    def _instruction_card(self, number_text: str, title: str, body: str, icon: ft.IconData) -> ft.Container:
        return ft.Container(
            col={"xs": 12, "sm": 4},
            padding=12 if self.compact else 14,
            bgcolor="#FAF8FC",
            border_radius=18,
            border=ft.Border.all(1, "#ECE8F0"),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=28,
                                height=28,
                                border_radius=14,
                                bgcolor=self.palette.secondary,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text(number_text, weight=ft.FontWeight.BOLD, color="#211D25"),
                            ),
                            ft.Icon(icon, color=self.palette.primary, size=22),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(title, weight=ft.FontWeight.BOLD, color="#211D25"),
                    ft.Text(body, size=12, color="#625C6B"),
                ],
                spacing=7,
            ),
        )

    def _prepare_players(self, _: Any) -> None:
        self.session.set_players(
            self.name_1.value if self.name_1 else None,
            self.name_2.value if self.name_2 else None,
        )
        first, second = self.session.players
        self._show_dialog(
            "Prontos para o desafio?",
            f"{first} e {second}, vocês percorrerão {self.session.phase_count} fases de educação financeira.\n\n"
            "Escolham uma questão à esquerda e encontrem a resolução correspondente à direita.",
            "Iniciar jogo",
            self._begin_game,
            secondary_label="Voltar",
        )

    # --------------------------------------------------------------- partida
    def _begin_game(self) -> None:
        self.session.new_game()
        self._enter_phase()

    def _start_phase(self, *, repeat: bool) -> None:
        self.session.start_phase(repeat=repeat)
        self._enter_phase()

    def _enter_phase(self) -> None:
        """Monta o tabuleiro da fase atual da sessão e liga o cronômetro."""

        self.phase_generation += 1
        self._close_whiteboard_sheet()
        self.whiteboard_visible = False
        # Cada nova fase recebe uma lousa nova. Isso evita reparentear o mesmo
        # Canvas entre raízes sucessivas do Flet.
        self._new_whiteboard()
        self._render_game_screen()
        if not self.admin:
            self.timer_future = self.page.run_task(self._timer_loop, self.phase_generation)

    async def _timer_loop(self, generation: int) -> None:
        while generation == self.phase_generation and self.session.phase_active:
            await asyncio.sleep(1)
            if generation != self.phase_generation:
                return
            timed_out = self.session.tick()
            self._refresh_timer()
            if timed_out:
                self._handle_timeout()
                return

    # ---------------------------------------------------------------- lousa
    def _new_whiteboard(self, drawing: Any = None) -> None:
        in_sheet = self.metrics.whiteboard_in_sheet
        page_height = self.page.height or 700
        self.whiteboard = Whiteboard(
            self.palette,
            self.dark_mode,
            canvas_height=max(200, min(420, page_height * 0.45)) if in_sheet else 230,
            on_close=self._toggle_whiteboard if in_sheet else None,
        )
        if drawing:
            self.whiteboard.restore(drawing)
        self.whiteboard_sheet = (
            ft.BottomSheet(
                content=ft.Container(content=self.whiteboard.panel, padding=ft.Padding.only(bottom=8)),
                # Sem arrastar: o gesto de arrastar é usado para escrever.
                draggable=False,
                scrollable=True,
                bgcolor=self.surface,
                on_dismiss=self._on_whiteboard_sheet_dismiss,
            )
            if in_sheet
            else None
        )

    def _close_whiteboard_sheet(self) -> None:
        if self.whiteboard_sheet is not None and self.whiteboard_visible:
            self.whiteboard_sheet.open = False

    def _on_whiteboard_sheet_dismiss(self, _: Any = None) -> None:
        if self.whiteboard_visible:
            self.whiteboard_visible = False
            self._update_whiteboard_button()
            self.page.update()

    def _toggle_whiteboard(self, _: Any = None) -> None:
        if self.whiteboard is None:
            return
        self.whiteboard_visible = not self.whiteboard_visible
        if self.whiteboard_sheet is not None:
            if self.whiteboard_visible:
                open_question = self.session.selected_question
                self.whiteboard.set_prompt(self.session.pairs_by_id[open_question].question if open_question else None)
                self.page.show_dialog(self.whiteboard_sheet)
            else:
                self.page.pop_dialog()
            self._update_whiteboard_button()
            self.page.update()
            return
        self.whiteboard.panel.visible = self.whiteboard_visible
        self._update_whiteboard_button()
        self.page.update(self.whiteboard.panel, self.whiteboard_button)

    def _update_whiteboard_button(self) -> None:
        label = "Fechar lousa" if self.whiteboard_visible else "Abrir lousa"
        icon = ft.Icons.CLOSE if self.whiteboard_visible else ft.Icons.DRAW
        button = self.whiteboard_button
        if isinstance(button, ft.IconButton):
            button.icon, button.tooltip = icon, label
        else:
            button.content, button.icon = label, icon

    # ------------------------------------------------------------ tabuleiro
    def _rebuild_game_screen(self) -> None:
        """Redesenha o tabuleiro (tema ou tamanho mudou) mantendo a lousa."""

        drawing = self.whiteboard.snapshot() if self.whiteboard else None
        self._close_whiteboard_sheet()
        self.whiteboard_visible = False
        self._new_whiteboard(drawing)
        self._render_game_screen()

    def _render_game_screen(self) -> None:
        self.screen = GAME_SCREEN
        session = self.session
        metrics = self.metrics
        self._apply_theme(dark=self.dark_mode)

        self.turn_text = ft.Text(weight=ft.FontWeight.BOLD, color=self.text_color, size=12 if self.compact else None)
        self.score_text = ft.Text(weight=ft.FontWeight.BOLD, color=self.text_color, size=12 if self.compact else None)
        self.timer_text = ft.Text(weight=ft.FontWeight.BOLD, color=self.text_color, size=12 if self.compact else None)
        self.timer_progress = ft.ProgressBar(
            value=1,
            bar_height=5,
            color=self.palette.secondary,
            bgcolor=self.border_color,
            border_radius=4,
        )
        self.overall_progress = ft.ProgressBar(
            value=0,
            bar_height=5,
            color=self.palette.primary,
            bgcolor=self.border_color,
            border_radius=4,
        )

        header = self._wide_header() if self.layout is Layout.WIDE else self._compact_header()

        self.focus_text = ft.Text(size=14 if self.compact else 15, color=self.text_color, weight=ft.FontWeight.W_500)
        self.focus_box = ft.Container(
            visible=False,
            padding=10,
            bgcolor=ft.Colors.with_opacity(0.10, self.palette.primary),
            border=ft.Border.all(1.5, self.palette.primary),
            border_radius=14,
            content=ft.Column(
                [
                    ft.Text("QUESTÃO ABERTA", size=10, weight=ft.FontWeight.BOLD, color=self.palette.primary),
                    self.focus_text,
                ],
                spacing=3,
            ),
        )

        # STRETCH: toda carta ocupa a largura da coluna, aberta ou fechada.
        self.left_cards = ft.Column(
            self._build_cards(QUESTION),
            spacing=metrics.spacing,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.right_cards = ft.Column(
            self._build_cards(RESOLUTION),
            spacing=metrics.spacing,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        board = ft.Row(
            [self._side_panel(QUESTION, self.left_cards), self._side_panel(RESOLUTION, self.right_cards)],
            spacing=metrics.spacing,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.advance_button = self._primary_button(
            ("Resultado" if self.compact else "Ver resultado") if session.is_last_phase else ("Avançar" if self.compact else "Avançar fase"),
            ft.Icons.ARROW_FORWARD,
            self._advance_phase,
            visible=session.advance_available,
            height=40 if self.compact else 48,
        )
        self.whiteboard_button = self._outline_button("Abrir lousa", ft.Icons.DRAW, self._toggle_whiteboard)
        self._update_whiteboard_button()
        actions = ft.Row(
            [
                self._outline_button("Repetir fase", ft.Icons.REPLAY, self._repeat_phase),
                self._outline_button("Reiniciar jogo", ft.Icons.HOME, self._confirm_restart),
                self.whiteboard_button,
                self.sounds.button(self.palette.primary),
                self.advance_button,
            ],
            alignment=ft.MainAxisAlignment.END,
            spacing=6 if self.compact else 8,
            tight=True,
        )

        if self.whiteboard is None:
            self._new_whiteboard()
        assert self.whiteboard is not None
        body_controls: list[ft.Control] = [board]
        if self.whiteboard_sheet is None:
            self.whiteboard.panel.width = SIDE_WHITEBOARD_WIDTH
            self.whiteboard.panel.visible = self.whiteboard_visible
            body_controls.append(self.whiteboard.panel)

        progress_label = ft.Text(
            f"Fase {session.phase_index + 1} de {session.phase_count}"
            if self.compact
            else f"Jornada financeira • fase {session.phase_index + 1} de {session.phase_count}",
            color=self.muted_color,
            size=11 if self.compact else 12,
        )
        progress = ft.Column([progress_label, self.overall_progress], spacing=3)
        if self.compact:
            progress.expand = True
        else:
            progress.width = 270
        progress_and_actions = ft.Row(
            [progress, actions],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=10,
        )
        self.game_body = ft.Row(
            body_controls,
            spacing=metrics.spacing,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        root = ft.Container(
            expand=True,
            bgcolor=self.background,
            padding=metrics.padding,
            content=ft.Column(
                [
                    *([s.admin_banner("Cronômetro desligado.")] if self.admin else []),
                    header,
                    progress_and_actions,
                    self.focus_box,
                    self.game_body,
                ],
                spacing=metrics.spacing,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                expand=True,
            ),
        )
        self._set_root(root)
        self._refresh_game_controls(update=False)
        self.page.update()

    def _timer_box(self, width: int) -> ft.Container:
        return ft.Container(
            width=width,
            content=ft.Column(
                [
                    ft.Row([ft.Icon(ft.Icons.TIMER, size=16, color=self.muted_color), self.timer_text], spacing=5),
                    self.timer_progress,
                ],
                spacing=4,
            ),
        )

    def _logo(self, size: int) -> ft.Container:
        return ft.Container(
            width=size,
            height=size,
            border_radius=size * 0.3,
            bgcolor=self.palette.primary,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.MEMORY, color=self.palette.on_primary, size=size * 0.58),
        )

    def _header_box(self, content: ft.Control) -> ft.Container:
        return ft.Container(
            padding=8 if self.compact else 10,
            bgcolor=self.surface,
            border_radius=16 if self.compact else 18,
            border=ft.Border.all(1, self.border_color),
            shadow=ft.BoxShadow(blur_radius=12, color="#14000000", offset=ft.Offset(0, 3)),
            content=content,
        )

    def _wide_header(self) -> ft.Container:
        phase = self.session.phase
        palette_dropdown = ft.Dropdown(
            label="Paleta",
            value=self.palette_key,
            width=132,
            dense=True,
            border_radius=10,
            leading_icon=ft.Icons.PALETTE,
            options=[ft.DropdownOption(key=key, text=value.name) for key, value in PALETTES.items()],
            on_select=self._change_palette,
        )
        dark_switch = ft.Switch(label="Escuro", value=self.dark_mode, on_change=self._toggle_dark_mode)
        return self._header_box(
            ft.Column(
                [
                    ft.Row(
                        [
                            self._logo(36),
                            ft.Column(
                                [
                                    ft.Text("Mente Financeira", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                                    ft.Text(phase.title, size=13, color=self.palette.primary, weight=ft.FontWeight.W_600),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                            self._status_chip(ft.Icons.PERSON, self.turn_text, self.palette.primary),
                            self._status_chip(ft.Icons.EMOJI_EVENTS, self.score_text, self.palette.secondary),
                            self._timer_box(145),
                        ],
                        spacing=9,
                    ),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        phase.objective,
                                        size=11,
                                        color=self.text_color,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(
                                        "Questão à esquerda → resolução à direita. Quem acerta continua.",
                                        size=10,
                                        color=self.muted_color,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            palette_dropdown,
                            dark_switch,
                        ],
                        spacing=9,
                    ),
                ],
                spacing=7,
            )
        )

    def _compact_header(self) -> ft.Container:
        """Cabeçalho de celular e tablet: título, menu de aparência e placar."""

        phase = self.session.phase
        palette_items = [
            ft.PopupMenuItem(
                content=f"Paleta {value.name}",
                icon=ft.Icons.PALETTE,
                checked=key == self.palette_key,
                data=key,
                on_click=self._change_palette,
            )
            for key, value in PALETTES.items()
        ]
        appearance_menu = ft.PopupMenuButton(
            icon=ft.Icons.TUNE,
            tooltip="Aparência",
            icon_color=self.text_color,
            items=[
                *palette_items,
                ft.PopupMenuItem(),  # divisória
                ft.PopupMenuItem(
                    content="Modo escuro",
                    icon=ft.Icons.DARK_MODE,
                    checked=self.dark_mode,
                    data=not self.dark_mode,
                    on_click=self._toggle_dark_mode,
                ),
            ],
        )
        return self._header_box(
            ft.Column(
                [
                    ft.Row(
                        [
                            self._logo(30 if self.compact else 36),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Mente Financeira",
                                        size=16 if self.compact else 19,
                                        weight=ft.FontWeight.BOLD,
                                        color=self.text_color,
                                    ),
                                    ft.Text(
                                        phase.title,
                                        size=12 if self.compact else 13,
                                        color=self.palette.primary,
                                        weight=ft.FontWeight.W_600,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                            appearance_menu,
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            self._status_chip(ft.Icons.PERSON, self.turn_text, self.palette.primary),
                            self._status_chip(ft.Icons.EMOJI_EVENTS, self.score_text, self.palette.secondary),
                            self._timer_box(110 if self.compact else 145),
                        ],
                        spacing=6,
                        wrap=True,
                        run_spacing=6,
                    ),
                ],
                spacing=6,
            )
        )

    def _status_chip(self, icon: ft.IconData, text: ft.Text, color: str) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=8 if self.compact else 9, vertical=5 if self.compact else 6),
            border_radius=15,
            bgcolor=ft.Colors.with_opacity(0.13, color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.35, color)),
            content=ft.Row([ft.Icon(icon, color=color, size=14 if self.compact else 16), text], spacing=5, tight=True),
        )

    def _side_panel(self, side: str, cards: ft.Column) -> ft.Container:
        is_question = side == QUESTION
        title = "QUESTÕES" if is_question else "RESOLUÇÕES"
        subtitle = "Comece por aqui" if is_question else "Encontre o par aqui"
        icon = ft.Icons.HELP_OUTLINE if is_question else ft.Icons.CALCULATE
        color = self.palette.primary if is_question else self.palette.secondary
        heading: list[ft.Control] = [ft.Text(title, size=self.metrics.side_title_size, weight=ft.FontWeight.BOLD, color=self.text_color)]
        if not self.compact:
            heading.append(ft.Text(subtitle, size=10, color=self.muted_color))
        return ft.Container(
            expand=True,
            padding=self.metrics.padding,
            bgcolor=self.surface,
            border_radius=14 if self.compact else 18,
            border=ft.Border.all(2, ft.Colors.with_opacity(0.40, color)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=24 if self.compact else 30,
                                height=24 if self.compact else 30,
                                border_radius=8 if self.compact else 9,
                                bgcolor=ft.Colors.with_opacity(0.13, color),
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(icon, color=color, size=15 if self.compact else 18),
                            ),
                            ft.Column(heading, spacing=0),
                        ],
                        spacing=6,
                    ),
                    cards,
                ],
                spacing=self.metrics.spacing,
                expand=True,
            ),
        )

    def _build_cards(self, side: str) -> list[ft.Control]:
        return [self._memory_card(side, pair_id, position + 1) for position, pair_id in enumerate(self.session.order(side))]

    def _memory_card(self, side: str, pair_id: str, position: int) -> ft.Container:
        session = self.session
        metrics = self.metrics
        pair = session.pairs_by_id[pair_id]
        selected = pair_id == session.selected(side)
        matched = pair_id in session.matched
        revealed = selected or matched
        is_question = side == QUESTION
        side_color = self.palette.primary if is_question else self.palette.secondary
        label = "QUESTÃO" if is_question else "RESOLUÇÃO"
        short_label = "Q" if is_question else "R"

        if revealed:
            body = pair.question if is_question else pair.resolution
            if self.compact:
                badge_text = "✓" if matched else ""
            else:
                badge_text = "PAR ENCONTRADO ✓" if matched else "CARTA ABERTA"
            content: ft.Control = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(short_label if self.compact else label, size=metrics.label_size, weight=ft.FontWeight.BOLD, color=side_color),
                            ft.Text(badge_text, size=metrics.label_size - 1, weight=ft.FontWeight.BOLD, color="#16805D" if matched else self.muted_color),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        body,
                        size=metrics.question_size if is_question else metrics.resolution_size,
                        weight=ft.FontWeight.W_600 if not is_question else ft.FontWeight.W_500,
                        color=self.text_color,
                        max_lines=metrics.question_lines,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=3 if self.compact else 5,
                alignment=ft.MainAxisAlignment.CENTER,
            )
            bgcolor = "#E7F8F0" if matched and not self.dark_mode else self.surface
            border_color = "#19A974" if matched else side_color
        else:
            hidden: list[ft.Control] = [
                ft.Icon(
                    ft.Icons.HELP_OUTLINE if is_question else ft.Icons.LOCK_OUTLINE,
                    color=side_color,
                    size=metrics.hidden_icon_size,
                ),
                ft.Text(
                    f"{short_label if self.compact else label} {position}",
                    weight=ft.FontWeight.BOLD,
                    color=self.text_color,
                    size=12 if self.compact else None,
                ),
            ]
            if not self.compact:
                hidden.append(ft.Text("Toque para revelar", size=10, color=self.muted_color))
            content = ft.Column(
                hidden,
                spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
            bgcolor = ft.Colors.with_opacity(0.07, side_color)
            border_color = ft.Colors.with_opacity(0.40, side_color)

        return ft.Container(
            content=content,
            expand=True,
            padding=6 if self.compact else 8,
            bgcolor=bgcolor,
            border=ft.Border.all(2 if revealed else 1, border_color),
            border_radius=12 if self.compact else 14,
            tooltip=None if self.compact or not revealed else body,
            ink=matched or session.phase_active,
            on_click=self._on_card_click,
            data=(side, pair_id),
            # Pares encontrados continuam tocáveis para rever a explicação.
            disabled=not matched and (not session.phase_active or session.locked),
            animate=180,
        )

    async def _on_card_click(self, event: Any) -> None:
        side, pair_id = event.control.data
        if pair_id in self.session.matched:
            if self.session.selected_resolution is None:  # sem comparação em andamento
                self._show_pair_review(pair_id)
            return
        match self.session.select(side, pair_id):
            case Selection.NEED_RESOLUTION:
                self._show_snack("Agora escolha uma resolução do lado direito.")
                return
            case Selection.NEED_QUESTION:
                self._show_snack("Comece escolhendo uma questão do lado esquerdo.")
                return
            case Selection.IGNORED:
                return
            case Selection.OPENED:
                self.sounds.play("virar")
                self._refresh_game_controls()
                return
            case Selection.READY:
                self.sounds.play("virar")

        # As duas cartas ficam visíveis por um instante antes da comparação.
        self._refresh_game_controls()
        generation = self.phase_generation
        await asyncio.sleep(REVEAL_DELAY_SECONDS)
        if generation != self.phase_generation or not self.session.phase_active:
            return

        outcome = self.session.resolve()
        self._refresh_game_controls()
        self.sounds.play("acerto" if outcome.matched else "erro")
        if outcome.matched and outcome.pair is not None:
            self._show_dialog("Par encontrado! 🎉", outcome.pair.explanation, "Continuar", self._after_match_explanation)
        else:
            self._show_snack(f"Ainda não! Agora é a vez de {self.session.current_player}.", error=True)

    def _show_pair_review(self, pair_id: str) -> None:
        pair = self.session.pairs_by_id[pair_id]
        # O cronômetro continua correndo: rever um par não é pausa para pensar.
        self._show_dialog("Par encontrado ✓", f"{pair.question}\n\n{pair.resolution}\n\n{pair.explanation}", "Fechar")

    def _after_match_explanation(self) -> None:
        if self.session.is_phase_complete:
            self._finish_phase()
        else:
            self.session.resume_timer()
            self._refresh_timer()

    def _finish_phase(self) -> None:
        self.sounds.play("vitoria")
        self.phase_generation += 1
        summary = self.session.finish_phase()
        self._refresh_game_controls()
        self._show_dialog(
            "Fase concluída! 🏆",
            f"{summary.message}\n\nDesempenho: {'⭐' * summary.stars}\n"
            f"Erros nesta fase: {summary.mistakes}\nTempo restante: {summary.time_left}s",
            "Ver tabuleiro",
        )

    def _handle_timeout(self) -> None:
        self.phase_generation += 1
        self._refresh_game_controls()
        self._show_dialog(
            "O tempo terminou ⏱️",
            f"A fase só é concluída quando os {len(self.session.pairs)} pares são encontrados. "
            "A pontuação obtida nesta tentativa será desfeita ao repetir.",
            "Repetir fase",
            self._repeat_phase,
            secondary_label="Reiniciar jogo",
            secondary_action=self._restart_game,
        )

    def _repeat_phase(self, _: Any = None) -> None:
        self._start_phase(repeat=True)

    def _advance_phase(self, _: Any = None) -> None:
        if not self.session.advance_available:
            return
        if self.session.is_last_phase:
            self._show_final_results()
            return
        self.session.advance()
        self._enter_phase()

    def _show_final_results(self) -> None:
        self._stop_background_tasks()
        session = self.session
        self._show_dialog(
            "Jornada concluída! 🎓",
            f"Vocês completaram as {session.phase_count} fases da Mente Financeira.\n\n"
            f"{session.final_result()}\nPlacar final: {session.scores[0]} × {session.scores[1]}\n"
            f"Tentativas incorretas: {session.total_mistakes}",
            "Jogar novamente",
            self._restart_game,
        )

    def _confirm_restart(self, _: Any = None) -> None:
        """Pede confirmação antes de descartar a partida (evita toque acidental)."""

        # O cronômetro segue correndo enquanto a pergunta está aberta.
        self._show_dialog(
            "Reiniciar o jogo?",
            "A partida atual será encerrada e o placar voltará a zero.",
            "Reiniciar",
            self._restart_game,
            secondary_label="Continuar jogando",
        )

    def _restart_game(self, _: Any = None) -> None:
        self._stop_background_tasks()
        self._close_whiteboard_sheet()
        self.whiteboard_visible = False
        self.whiteboard = None
        self.whiteboard_sheet = None
        self._show_start_screen()

    # ------------------------------------------------------------ aparência
    def _change_palette(self, event: Any) -> None:
        # Dropdown (computador) envia ``value``; item de menu (celular), ``data``.
        control = event.control
        value = str(getattr(control, "value", None) or control.data)
        if value not in PALETTES:
            return
        self.palette_key = value
        self._save_settings()
        self._rebuild_game_screen()

    def _toggle_dark_mode(self, event: Any) -> None:
        # Switch (computador) envia ``value``; item de menu (celular), ``data``.
        control = event.control
        value = getattr(control, "value", None)
        self.dark_mode = bool(control.data if value is None else value)
        self._save_settings()
        self._rebuild_game_screen()

    # ----------------------------------------------------------- atualização
    def _refresh_game_controls(self, *, update: bool = True) -> None:
        session = self.session
        self.turn_text.value = f"Vez: {session.current_player}"
        self.score_text.value = f"{session.scores[0]} × {session.scores[1]}" if self.compact else f"Placar: {session.scores[0]} × {session.scores[1]}"
        self.left_cards.controls = self._build_cards(QUESTION)
        self.right_cards.controls = self._build_cards(RESOLUTION)
        self.advance_button.visible = session.advance_available
        self.overall_progress.value = session.overall_progress
        # No celular a carta mostra só parte do enunciado; a faixa acima do
        # tabuleiro mostra a questão aberta por inteiro.
        open_question = session.selected_question
        show_focus = open_question is not None and self.compact
        self.focus_box.visible = show_focus
        self.focus_text.value = session.pairs_by_id[open_question].question if show_focus and open_question else ""
        self._refresh_timer(update=False)
        if update:
            self.page.update()

    def _refresh_timer(self, *, update: bool = True) -> None:
        session = self.session
        warning = session.time_left <= TIMER_WARNING_SECONDS
        paused = " • pausa" if session.timer_paused and session.phase_active else ""
        self.timer_text.value = "sem limite" if self.admin else f"{session.time_left}s{paused}"
        self.timer_text.color = "#D22D3D" if warning else self.text_color
        self.timer_progress.value = session.time_left / session.timer_seconds
        self.timer_progress.color = "#D22D3D" if warning else self.palette.secondary
        if update:
            self.page.update(self.timer_text, self.timer_progress)

    # -------------------------------------------------------------- avisos
    def _show_snack(self, message: str, *, error: bool = False) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                ft.Text(message, color="#FFFFFF"),
                bgcolor="#B3261E" if error else self.palette.primary,
                behavior=ft.SnackBarBehavior.FLOATING,
                show_close_icon=True,
            )
        )

    def _show_dialog(
        self,
        title: str,
        message: str,
        primary_label: str,
        primary_action: Any = None,
        *,
        secondary_label: str | None = None,
        secondary_action: Any = None,
    ) -> None:
        def close_and_run(action: Any) -> Any:
            def handler(_: Any) -> None:
                self.page.pop_dialog()
                if action is not None:
                    action()

            return handler

        actions: list[ft.Control] = []
        if secondary_label:
            actions.append(ft.TextButton(secondary_label, on_click=close_and_run(secondary_action)))
        actions.append(
            ft.Button(
                primary_label,
                on_click=close_and_run(primary_action),
                style=ft.ButtonStyle(
                    bgcolor=self.palette.primary,
                    color=self.palette.on_primary,
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
            )
        )
        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                icon=ft.Icon(ft.Icons.AUTO_AWESOME, color=self.palette.secondary, size=34),
                title=ft.Text(title, weight=ft.FontWeight.BOLD),
                # Rola só se a explicação não couber (janela do tamanho do texto).
                content=ft.Text(message, selectable=True),
                scrollable=True,
                actions=actions,
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )
