"""Nível 1 — jogo da memória tradicional com 16 cartas."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, Protocol

import flet as ft

from mente_financeira.admin import admin_ativo
from mente_financeira.content.memory_deck import Concept
from mente_financeira.core.memory_game import Flip, MemoryGame, Mode
from mente_financeira.core.percent_challenge import PERCENT_KIT, Challenge, ChallengeKit
from mente_financeira.storage import SettingsStore
from mente_financeira.ui import style as s
from mente_financeira.ui.sounds import SoundEffects
from mente_financeira.ui.layout import Layout, layout_for
from mente_financeira.ui.theme import PALETTES
from mente_financeira.ui.whiteboard import Whiteboard

COLUMNS = 4
MISMATCH_DELAY_SECONDS = 0.9
RESULT_DELAY_SECONDS = 0.6
FLIP_MS = 260
CONCEPT_PANEL_MIN_WIDTH = 420
COMPACT_TIP_HEIGHT = 150


class OnlineSeat(Protocol):
    """Lugar desta tela numa partida online (o jogo é compartilhado)."""

    seat: int  # 0 ou 1: qual jogador da partida está nesta tela

    def changed(self) -> None:
        """Avisa a tela do adversário que o jogo mudou."""


class MemoryScreen:
    def __init__(
        self,
        page: ft.Page,
        game: MemoryGame,
        *,
        on_home: Callable[[], None],
        on_level2: Callable[[], None],
        sounds: SoundEffects | None = None,
        challenges: ChallengeKit = PERCENT_KIT,
        online: OnlineSeat | None = None,
    ) -> None:
        self.page = page
        self.game = game
        self.challenges = challenges  # Desafio Relâmpago do Duelo, conforme a trilha
        # Partida online: cada jogador tem a sua tela, com o mesmo jogo.
        self.online = online
        self.seen_learned = len(game.learned)
        self.seen_turn = game.turn
        self.result_shown = False
        self.on_home = on_home
        self.on_level2 = on_level2
        self.sounds = sounds or SoundEffects(page, SettingsStore())
        self.layout = layout_for(page.width)
        self.generation = 0
        self.last_concept: Concept | None = None
        self.cards: list[ft.Container] = []
        self.switchers: list[ft.AnimatedSwitcher] = []
        self.stats = ft.Row()
        self.tip_switcher = ft.AnimatedSwitcher(content=ft.Container())
        self.learned_row = ft.Column()
        self.learned_title = ft.Text()
        self.locked_note = ft.Text()
        self.panel_count = ft.Text()
        self.panel_progress = ft.ProgressBar()
        self.card_size = 80.0

        # Desafio Relâmpago (Duelo)
        self.overlay = ft.Container(visible=False)
        self.challenge: Challenge | None = None
        self.challenge_choice: int | None = None
        self.challenge_feedback = ""
        self.challenge_board: Whiteboard | None = None
        self.challenge_board_visible = False
        self.option_boxes: list[ft.Container] = []
        self.feedback_box = ft.Container()
        self.feedback_switcher = ft.AnimatedSwitcher(content=ft.Container())
        self.continue_button = ft.Container()
        self.board_button = ft.OutlinedButton()
        self.image_panel = ft.Container()
        self.challenge_side: ft.Column | None = None

        # Modo administrador: cronômetro desligado e gabarito à mão.
        self.admin = admin_ativo()
        self.show_answers = False
        self.answers_button = ft.TextButton()

    # ------------------------------------------------------------ ciclo
    def show(self) -> None:
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = s.BG_TOP
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()
        self.generation += 1
        # Online, só a tela do primeiro jogador conta o tempo (o jogo é um só).
        if not self.admin and (self.online is None or self.online.seat == 0):
            self.page.run_task(self._clock, self.generation)

    def stop(self) -> None:
        self.generation += 1
        self.game.stop()

    def on_resize(self, event: Any) -> None:
        self.layout = layout_for(getattr(event, "width", None) or self.page.width)
        # O tamanho das cartas depende da janela: redesenha sempre, mantendo o jogo.
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()

    async def _clock(self, generation: int) -> None:
        while generation == self.generation and self.game.active:
            await asyncio.sleep(1)
            if generation != self.generation:
                return
            self.game.tick()
            self._refresh_stats()
            self.page.update()

    # ------------------------------------------------------------ medidas
    @property
    def compact(self) -> bool:
        return self.layout is Layout.COMPACT

    def _measure(self) -> tuple[float, float]:
        """Devolve (tamanho da carta, espaçamento) para caber na tela."""

        width = self.page.width or 1280
        height = self.page.height or 720
        gap = 8 if self.compact else 12
        top_bar = 112 if self.compact else 76
        if self.compact:
            side = min(width - 24, height - top_bar - COMPACT_TIP_HEIGHT - 40)
        else:
            # O painel de conceitos fica com o resto da largura (no mínimo 420 px).
            side = min(width - CONCEPT_PANEL_MIN_WIDTH - 72, height - top_bar - 40)
        side = max(side, 4 * 56 + 3 * gap)
        return (side - (COLUMNS - 1) * gap) / COLUMNS, gap

    # ------------------------------------------------------------ desenho
    def build(self) -> ft.Control:
        self.card_size, gap = self._measure()
        self.cards = []
        self.switchers = []
        rows: list[ft.Control] = []
        for row in range(len(self.game.cards) // COLUMNS):
            items = [self._card(row * COLUMNS + col) for col in range(COLUMNS)]
            rows.append(ft.Row(items, spacing=gap, tight=True))
        grid = ft.Column(rows, spacing=gap, tight=True)

        concept_panel = self._concept_panel()
        if self.compact:
            body: ft.Control = ft.Column(
                [ft.Row([grid], alignment=ft.MainAxisAlignment.CENTER), concept_panel],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        else:
            # Painel com a mesma altura do tabuleiro, ocupando o resto da largura.
            concept_panel.height = COLUMNS * self.card_size + (COLUMNS - 1) * gap
            concept_panel.expand = True
            body = ft.Row(
                [grid, concept_panel],
                spacing=24,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )

        self._refresh_stats()
        board_screen = ft.Container(
            left=0,
            top=0,
            right=0,
            bottom=0,
            gradient=s.background(),
            padding=12 if self.compact else 20,
            content=ft.Column(
                [*self._admin_bar(), self._top_bar(), body],
                spacing=12 if self.compact else 18,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )
        # Camada do Desafio Relâmpago, por cima do tabuleiro.
        self.overlay = ft.Container(left=0, top=0, right=0, bottom=0, visible=False)
        if self.challenge is not None:  # redesenho (ex.: girou a tela) no meio do desafio
            drawing = self.challenge_board.snapshot() if self.challenge_board else None
            self.challenge_board = self._new_challenge_board(drawing)
            self._build_overlay()
        return ft.SafeArea(expand=True, content=ft.Stack([board_screen, self.overlay], expand=True))

    def _top_bar(self) -> ft.Control:
        mode_text = "Modo Solo" if self.game.mode is Mode.SOLO else "Modo Duelo"
        if self.online is not None:
            mode_text = "Duelo online"
        # Online não há "nova partida": os dois precisariam concordar.
        restart = [] if self.online is not None else [
            ft.IconButton(ft.Icons.REPLAY_ROUNDED, icon_color=s.WHITE, tooltip="Nova partida", on_click=self._restart)
        ]
        title = ft.Row(
            [
                ft.IconButton(ft.Icons.HOME_ROUNDED, icon_color=s.WHITE, tooltip="Início", on_click=self._confirm_home),
                ft.Column(
                    [
                        s.gradient_text("MEMÓRIA FINANCEIRA", 18 if self.compact else 24, [s.YELLOW, s.PINK]),
                        ft.Text(f"Nível 1 • {mode_text}", size=12, color=s.MUTED),
                    ],
                    spacing=0,
                    expand=True,
                ),
                self.sounds.button(s.WHITE),
                *restart,
            ],
            spacing=6,
        )
        self.stats = ft.Row(spacing=8, wrap=True, run_spacing=8)
        if self.compact:
            return ft.Column([title, self.stats], spacing=6)
        return ft.Row([ft.Container(title, expand=True), self.stats], spacing=12)

    def _card(self, index: int) -> ft.Container:
        switcher = ft.AnimatedSwitcher(
            content=self._card_face(index),
            transition=ft.AnimatedSwitcherTransition.SCALE,
            duration=FLIP_MS,
            reverse_duration=FLIP_MS,
            switch_in_curve=ft.AnimationCurve.EASE_OUT_BACK,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
        )
        card = ft.Container(
            width=self.card_size,
            height=self.card_size,
            border_radius=self.card_size * 0.18,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            data=index,
            on_click=self._on_card_click,
            content=switcher,
            animate_scale=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
        )
        self._style_card(card, index)
        self.cards.append(card)
        self.switchers.append(switcher)
        return card

    def _admin_bar(self) -> list[ft.Control]:
        if not self.admin:
            return []
        self.answers_button = ft.TextButton(
            "Esconder gabarito" if self.show_answers else "Mostrar gabarito",
            icon=ft.Icons.VISIBILITY_OFF_ROUNDED if self.show_answers else ft.Icons.VISIBILITY_ROUNDED,
            on_click=self._toggle_answers,
            style=ft.ButtonStyle(color="#2B1A00"),
        )
        return [s.admin_banner("Cronômetro desligado.", [self.answers_button])]

    def _toggle_answers(self, _: Any = None) -> None:
        """Mostra/esconde a frente de todas as cartas (não conta como jogada)."""

        self.show_answers = not self.show_answers
        self.answers_button.content = "Esconder gabarito" if self.show_answers else "Mostrar gabarito"
        self.answers_button.icon = ft.Icons.VISIBILITY_OFF_ROUNDED if self.show_answers else ft.Icons.VISIBILITY_ROUNDED
        for index in range(len(self.cards)):
            self._refresh_card(index)
        self.page.update()

    def _card_face(self, index: int) -> ft.Control:
        size = self.card_size
        if not (self.game.is_revealed(index) or self.show_answers):
            return ft.Image(
                key=f"verso-{index}",
                src=self.game.deck.back_image,
                width=size,
                height=size,
                fit=ft.BoxFit.COVER,
                semantics_label="Carta virada",
            )
        concept = self.game.cards[index]
        # Frente no estilo carta de baralho: fundo claro com moldura na cor do
        # conceito, o nome numa faixa colorida em cima e o desenho embaixo.
        # Assim ninguém confunde carta aberta com o verso escuro.
        band = size * 0.27
        picture = min(size - band - size * 0.12, size * 0.62)
        return ft.Container(
            key=f"frente-{index}",
            width=size,
            height=size,
            bgcolor="#FFF8EC",
            border=ft.Border.all(max(2, size * 0.025), concept.color),
            border_radius=size * 0.18,
            content=ft.Column(
                [
                    ft.Container(
                        height=band,
                        bgcolor=concept.color,
                        padding=ft.Padding.symmetric(horizontal=4),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            concept.name,
                            size=max(9, size * 0.095),
                            weight=ft.FontWeight.BOLD,
                            color=s.WHITE,
                            text_align=ft.TextAlign.CENTER,
                            # Duas linhas: nomes como "Reserva de emergência" cabem inteiros.
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Image(
                            src=concept.image,
                            width=picture,
                            height=picture,
                            fit=ft.BoxFit.CONTAIN,
                            border_radius=picture * 0.2,
                            semantics_label=concept.name,
                        ),
                    ),
                ],
                spacing=0,
            ),
        )

    def _style_card(self, card: ft.Container, index: int) -> None:
        matched = index in self.game.matched
        face_up = index in self.game.face_up
        if matched:
            card.border = ft.Border.all(3, s.GREEN)
            card.shadow = ft.BoxShadow(blur_radius=18, color=ft.Colors.with_opacity(0.6, s.GREEN))
            card.scale = 0.96
        elif face_up:
            card.border = ft.Border.all(3, s.YELLOW)
            card.shadow = ft.BoxShadow(blur_radius=18, color=ft.Colors.with_opacity(0.6, s.YELLOW))
            card.scale = 1.04
        else:
            card.border = ft.Border.all(1, s.GLASS_BORDER)
            card.shadow = ft.BoxShadow(blur_radius=10, color="#55000000", offset=ft.Offset(0, 4))
            card.scale = 1.0
        card.ink = not matched

    # ------------------------------------------------- Conceitos descobertos
    def _concept_panel(self) -> ft.Container:
        """Painel de leitura: o conceito em destaque e a lista dos descobertos."""

        compact = self.compact
        self.tip_switcher = ft.AnimatedSwitcher(
            content=self._tip_content(self.last_concept),
            transition=ft.AnimatedSwitcherTransition.SCALE,
            duration=350,
            reverse_duration=150,
            switch_in_curve=ft.AnimationCurve.EASE_OUT_BACK,
        )
        self.panel_count = ft.Text(size=20 if compact else 24, weight=ft.FontWeight.W_900, color=s.YELLOW)
        self.panel_progress = ft.ProgressBar(value=0, bar_height=8, border_radius=4, color=s.GREEN, bgcolor=s.GLASS)
        self.learned_title = ft.Text(
            "JÁ DESCOBERTOS • toque para rever", size=12, weight=ft.FontWeight.BOLD, color=s.MUTED
        )
        self.learned_row = ft.Column(spacing=8, tight=True)
        self.locked_note = ft.Text(size=13, color=s.MUTED, text_align=ft.TextAlign.CENTER)
        self._refresh_learned()
        return s.glass(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "💡 CONCEITOS DESCOBERTOS",
                                size=13 if compact else 15,
                                weight=ft.FontWeight.W_900,
                                color=s.CYAN,
                                expand=True,
                            ),
                            self.panel_count,
                        ]
                    ),
                    self.panel_progress,
                    self.tip_switcher,
                    self.learned_title,
                    self.learned_row,
                    self.locked_note,
                ],
                spacing=12,
                # No computador o painel tem altura fixa e rola por dentro;
                # no celular quem rola é a página.
                scroll=None if compact else ft.ScrollMode.AUTO,
                tight=compact,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=14 if compact else 20,
        )

    def _tip_content(self, concept: Concept | None) -> ft.Control:
        """Cartão em destaque: regras (antes do 1º par) ou o conceito escolhido."""

        compact = self.compact
        if concept is None:
            rules = (
                "Vire duas cartas por vez e encontre os pares iguais. "
                "Cada par revela um conceito de educação financeira, com curiosidade e exemplo!"
            )
            if self.game.mode is Mode.DUEL:
                rules += (
                    f"\n\n⚡ No Duelo, cada par vale um Desafio Relâmpago {self.challenges.topic}: "
                    "acerte para continuar jogando; errou, passa a vez."
                )
            return ft.Container(
                key="intro",
                padding=16,
                border_radius=20,
                bgcolor=ft.Colors.with_opacity(0.10, s.WHITE),
                content=ft.Column(
                    [
                        ft.Text("🧠 COMO JOGAR", size=14, weight=ft.FontWeight.W_900, color=s.YELLOW),
                        ft.Text(rules, size=15 if compact else 16, color=s.WHITE),
                    ],
                    spacing=8,
                    tight=True,
                ),
            )
        is_newest = bool(self.game.learned) and concept is self.game.learned[-1]
        return ft.Container(
            key=f"dica-{concept.id}",
            padding=16 if compact else 20,
            border_radius=22,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[concept.color, "#2A0E61"],
            ),
            shadow=ft.BoxShadow(blur_radius=24, color=ft.Colors.with_opacity(0.45, concept.color)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=64 if compact else 80,
                                height=64 if compact else 80,
                                border_radius=18,
                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                border=ft.Border.all(2, ft.Colors.with_opacity(0.6, s.WHITE)),
                                content=ft.Image(src=concept.image, fit=ft.BoxFit.COVER),
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "✨ NOVO CONCEITO!" if is_newest else "CONCEITO",
                                        size=12,
                                        weight=ft.FontWeight.W_900,
                                        color=s.YELLOW,
                                    ),
                                    ft.Text(concept.name, size=22 if compact else 26, weight=ft.FontWeight.W_900, color=s.WHITE),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                        ],
                        spacing=14,
                    ),
                    ft.Text("💡 VOCÊ SABIA?", size=13, weight=ft.FontWeight.W_900, color=s.YELLOW),
                    ft.Text(concept.tip, size=16 if compact else 17, color=s.WHITE, weight=ft.FontWeight.W_500),
                    ft.Container(
                        padding=14,
                        border_radius=16,
                        bgcolor=ft.Colors.with_opacity(0.16, s.WHITE),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.3, s.WHITE)),
                        content=ft.Column(
                            [
                                ft.Text("📌 NA PRÁTICA", size=13, weight=ft.FontWeight.W_900, color=s.YELLOW),
                                ft.Text(concept.example, size=15 if compact else 16, color=s.WHITE),
                            ],
                            spacing=6,
                            tight=True,
                        ),
                    ),
                ],
                spacing=10,
                tight=True,
            ),
        )

    def _show_concept(self, event: Any) -> None:
        """Toque num conceito da lista: ele volta para o destaque."""

        concept = event.control.data
        self.last_concept = concept
        self.tip_switcher.content = self._tip_content(concept)
        self._refresh_learned()
        self.page.update()

    # ------------------------------------------------------------ atualização
    def _refresh_card(self, index: int) -> None:
        self.switchers[index].content = self._card_face(index)
        self._style_card(self.cards[index], index)

    def _refresh_learned(self) -> None:
        game = self.game
        found, total = len(game.learned), game.pairs
        self.panel_count.value = f"{found}/{total}"
        self.panel_progress.value = found / total
        # Lista do mais recente para o mais antigo; o que está em destaque
        # aparece marcado.
        self.learned_row.controls = [self._learned_item(concept) for concept in reversed(game.learned)]
        self.learned_title.visible = found > 0
        missing = total - found
        self.locked_note.value = (
            f"🔒 Faltam {missing} conceito{'s' if missing > 1 else ''} para descobrir"
            if missing
            else "🏆 Você descobriu todos os conceitos desta partida!"
        )

    def _learned_item(self, concept: Concept) -> ft.Container:
        selected = concept is self.last_concept
        return ft.Container(
            data=concept,
            on_click=self._show_concept,
            ink=True,
            padding=10,
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.22 if selected else 0.08, concept.color if selected else s.WHITE),
            border=ft.Border.all(2 if selected else 1, concept.color if selected else s.GLASS_BORDER),
            content=ft.Row(
                [
                    ft.Container(
                        width=46,
                        height=46,
                        border_radius=12,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        content=ft.Image(src=concept.image, fit=ft.BoxFit.COVER),
                    ),
                    ft.Column(
                        [
                            ft.Text(concept.name, size=15, weight=ft.FontWeight.W_900, color=s.WHITE),
                            ft.Text(concept.tip, size=12, color=s.MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=s.MUTED),
                ],
                spacing=12,
            ),
        )

    def _refresh_stats(self) -> None:
        game = self.game
        found = s.chip(f"{game.found_pairs}/{game.pairs} pares", icon=ft.Icons.CHECK_CIRCLE_ROUNDED, color=s.GREEN)
        if game.mode is Mode.SOLO:
            minutes, seconds = divmod(game.elapsed, 60)
            chips = [
                s.chip(f"{minutes}:{seconds:02d}", icon=ft.Icons.TIMER_ROUNDED, color=s.CYAN),
                s.chip(f"{game.moves} jogadas", icon=ft.Icons.TOUCH_APP_ROUNDED, color=s.YELLOW),
                found,
            ]
        else:
            chips = [self._player_chip(i) for i in range(2)] + [found]
        self.stats.controls = chips

    def _player_chip(self, index: int) -> ft.Container:
        active = self.game.turn == index and self.game.active
        color = s.PINK if index == 0 else s.CYAN
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.45 if active else 0.12, color),
            border=ft.Border.all(2 if active else 1, color),
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED if active else ft.Icons.PERSON_ROUNDED, color=s.WHITE, size=16),
                    ft.Text(f"{self.game.players[index]}: {self.game.scores[index]}", size=12, weight=ft.FontWeight.BOLD, color=s.WHITE),
                ],
                spacing=4,
                tight=True,
            ),
        )

    # ------------------------------------------------------------ jogada
    async def _on_card_click(self, event: Any) -> None:
        index = event.control.data
        if self.online is not None and self.game.turn != self.online.seat:
            if self.game.active:
                self._snack(f"Espere: agora é a vez de {self.game.current_player}.")
                self.page.update()
            return
        result = self.game.flip(index)
        if result is Flip.IGNORED:
            return
        self.sounds.play("virar")
        self._refresh_card(index)
        self.page.update()
        self._notify()
        if result is Flip.OPENED:
            return

        first, second = self.game.face_up
        generation = self.generation
        # Erro: as duas cartas ficam à mostra um instante antes de desvirar.
        if self.game.cards[first].id != self.game.cards[second].id:
            await asyncio.sleep(MISMATCH_DELAY_SECONDS)
            if generation != self.generation:
                return
        outcome = self.game.resolve()
        for i in (first, second):
            self._refresh_card(i)
        self._refresh_stats()
        # O último par já leva ao resultado, que tem o som de vitória.
        if not self.game.is_complete:
            self.sounds.play("acerto" if outcome.matched else "erro")
        if outcome.matched:
            self.last_concept = outcome.concept
            self.tip_switcher.content = self._tip_content(outcome.concept)
            self._refresh_learned()
            if outcome.challenge:
                self._open_challenge()
        elif self.game.mode is Mode.DUEL:
            self._snack(f"Errou! Agora é a vez de {self.game.current_player}.")
        self.seen_learned, self.seen_turn = len(self.game.learned), self.game.turn
        self.page.update()
        self._notify()
        if self.game.is_complete:
            await asyncio.sleep(RESULT_DELAY_SECONDS)
            if generation == self.generation:
                self._show_result()

    # ------------------------------------------------------ Desafio Relâmpago
    def _open_challenge(self) -> None:
        self.challenge = self.challenges.make(self.game.rng)
        self.challenge_choice = None
        self.challenge_feedback = ""
        self.challenge_board_visible = False
        self.challenge_board = self._new_challenge_board()
        self._build_overlay()

    def _new_challenge_board(self, drawing: Any = None) -> Whiteboard:
        # A tela do desafio não rola (o arrasto é da lousa), então a lousa se
        # ajusta à altura. No computador ela ocupa o painel da imagem; no
        # celular, também, mas encolhe em telas baixas.
        height = self.page.height or 720
        if self.compact:
            canvas = max(110, min(220, height - 620))
        else:
            canvas = max(200, min(340, height - 330))
        board = Whiteboard(PALETTES["kids"], dark_mode=False, canvas_height=canvas, show_title=False)
        if drawing:
            board.restore(drawing)
        return board

    def _build_overlay(self) -> None:
        """Monta a tela inteira do desafio. Depois, só as propriedades mudam.

        Computador: faixa no topo; à esquerda, o painel com a imagem da situação
        (que dá lugar à lousa ou à comemoração); à direita, o cartão da pergunta.
        Celular: a mesma coisa, empilhada.
        """

        challenge = self.challenge
        assert challenge is not None and self.challenge_board is not None
        compact = self.compact
        player_color = s.PINK if self.game.turn == 0 else s.CYAN
        panel_side = 420

        # ---- alternativas em pílulas "A. R$ 48,00"
        self.option_boxes = [
            ft.Container(
                expand=True,
                height=58 if compact else 74,
                border_radius=40,
                padding=ft.Padding.symmetric(horizontal=10 if compact else 26),
                alignment=ft.Alignment.CENTER if compact else ft.Alignment.CENTER_LEFT,
                data=index,
                on_click=self._answer_challenge,
                animate=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
                content=ft.Row(
                    [
                        ft.Text(f"{'ABCD'[index]}.", size=16 if compact else 24, weight=ft.FontWeight.W_900, color=s.YELLOW),
                        ft.Text(option, size=16 if compact else 24, weight=ft.FontWeight.W_700, color=s.WHITE),
                    ],
                    spacing=6 if compact else 8,
                    tight=True,
                ),
            )
            for index, option in enumerate(challenge.options)
        ]
        options = ft.Column(
            [ft.Row(self.option_boxes[0:2], spacing=12), ft.Row(self.option_boxes[2:4], spacing=12)],
            spacing=12,
        )
        admin_hint: list[ft.Control] = [s.admin_banner(f"Gabarito: {challenge.answer}")] if self.admin else []

        # ---- cartão da pergunta
        question_card = ft.Container(
            padding=18 if compact else 28,
            border_radius=28,
            bgcolor="#E6241452",
            border=ft.Border.all(2, ft.Colors.with_opacity(0.8, s.CYAN)),
            shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.35, s.CYAN)),
            expand=not compact,
            content=ft.Column(
                [
                    ft.Text(challenge.label, size=13 if compact else 15, weight=ft.FontWeight.W_900, color=s.YELLOW),
                    ft.Text(challenge.item, size=17 if compact else 22, weight=ft.FontWeight.W_700, color=s.CYAN),
                    ft.Text(challenge.question, size=19 if compact else 27, weight=ft.FontWeight.W_700, color=s.WHITE),
                    options,
                    *admin_hint,
                ],
                spacing=10 if compact else 16,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )

        # ---- painel da esquerda: imagem, lousa ou comemoração
        self.image_panel = ft.Container(
            height=170 if compact else panel_side,
            padding=12,
            border_radius=28,
            bgcolor="#E61B0B45",
            border=ft.Border.all(2, ft.Colors.with_opacity(0.8, s.CYAN)),
            shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.35, s.CYAN)),
            alignment=ft.Alignment.CENTER,
            # Tamanho explícito: sem ele o SVG fica no tamanho natural (200 px).
            content=ft.Image(
                src=challenge.image,
                width=146 if compact else panel_side - 28,
                height=146 if compact else panel_side - 28,
                fit=ft.BoxFit.CONTAIN,
                semantics_label=challenge.item,
            ),
        )
        # A comemoração (ou a correção) entra com um "pulo" de escala.
        self.feedback_switcher = ft.AnimatedSwitcher(
            content=ft.Container(key="vazio"),
            transition=ft.AnimatedSwitcherTransition.SCALE,
            duration=550,
            reverse_duration=150,
            switch_in_curve=ft.AnimationCurve.ELASTIC_OUT,
        )
        self.feedback_box = ft.Container(content=self.feedback_switcher)
        self.continue_button = s.pill_button(
            "", ft.Icons.ARROW_FORWARD_ROUNDED, self._close_challenge, height=54 if compact else 62
        )
        self.board_button = ft.OutlinedButton(
            on_click=self._toggle_challenge_board,
            height=42,
            style=ft.ButtonStyle(
                color=s.CYAN,
                side=ft.BorderSide(2, s.CYAN),
                shape=ft.RoundedRectangleBorder(radius=16),
                text_style=ft.TextStyle(size=15, weight=ft.FontWeight.BOLD),
            ),
        )
        left_panel = ft.Column(
            [self.image_panel, self.challenge_board.panel, self.feedback_box, self.continue_button],
            spacing=14,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        # ---- faixa do topo
        top = ft.Row(
            [
                s.chip("DESAFIO RELÂMPAGO", icon=ft.Icons.BOLT_ROUNDED, color=s.YELLOW, size=13 if compact else 15),
                ft.Text(
                    f"Vez de {self.game.current_player} — acerte para continuar jogando!",
                    size=14 if compact else 18,
                    weight=ft.FontWeight.W_900,
                    color=player_color,
                    expand=True,
                    visible=not compact,
                ),
                ft.Container(expand=compact),
                self.board_button,
            ],
            spacing=16,
        )
        player_line = ft.Text(
            f"Vez de {self.game.current_player} — acerte para continuar jogando!",
            size=14,
            weight=ft.FontWeight.W_900,
            color=player_color,
            visible=compact,
        )

        self.challenge_side = None
        if compact:
            # Celular: o botão de seguir fica logo abaixo do cartão.
            left_panel.controls.remove(self.continue_button)
            body: ft.Control = ft.Column(
                [top, player_line, left_panel, question_card, self.continue_button],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        else:
            left_panel.width = panel_side
            body = ft.Column(
                [
                    top,
                    ft.Row([left_panel, question_card], spacing=28, vertical_alignment=ft.CrossAxisAlignment.START),
                ],
                spacing=22,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )

        # Tela inteira, com fundo próprio (o tabuleiro fica escondido).
        self.overlay.content = ft.Container(
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#12082E", "#2A0E61", "#4A0C6E"],
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=14) if compact else 32,
            alignment=ft.Alignment.CENTER,
            content=ft.Container(content=body, width=None if compact else 1180),
        )
        self.overlay.visible = True
        self._apply_challenge_state()

    def _celebration(self, correct: bool) -> ft.Control:
        """Bloco de destaque: comemoração no acerto, correção no erro."""

        compact = self.compact
        other = self.game.players[1 - self.game.turn]
        if correct:
            colors, emoji = [s.GREEN, s.CYAN], "🎉"
            lines: list[ft.Control] = [
                ft.Text(
                    self.challenge_feedback,
                    size=26 if compact else 32,
                    weight=ft.FontWeight.W_900,
                    color="#0B1E3F",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    f"{self.game.current_player}, a vez continua sua!",
                    size=15 if compact else 18,
                    weight=ft.FontWeight.BOLD,
                    color="#0B1E3F",
                    text_align=ft.TextAlign.CENTER,
                ),
            ]
        else:
            colors, emoji = ["#FF4D6D", s.ORANGE], "💡"
            first, _, rest = self.challenge_feedback.partition("\n")
            lines = [
                ft.Text(first, size=20 if compact else 25, weight=ft.FontWeight.W_900, color=s.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text(rest, size=14 if compact else 17, weight=ft.FontWeight.W_600, color=s.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text(f"A vez passa para {other}.", size=14 if compact else 16, color=s.WHITE, text_align=ft.TextAlign.CENTER),
            ]
        return ft.Container(
            key=f"feedback-{correct}",
            padding=ft.Padding.symmetric(horizontal=18, vertical=14 if compact else 22),
            border_radius=28,
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT, colors=colors),
            shadow=ft.BoxShadow(blur_radius=36, spread_radius=2, color=ft.Colors.with_opacity(0.6, colors[0])),
            content=ft.Column(
                [ft.Text(emoji, size=36 if compact else 56), *lines],
                spacing=4,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _apply_challenge_state(self) -> None:
        challenge = self.challenge
        assert challenge is not None and self.challenge_board is not None
        choice = self.challenge_choice
        answered = choice is not None
        for index, box in enumerate(self.option_boxes):
            if not answered:
                box.bgcolor, box.border = "#3A1C8C", ft.Border.all(1.5, ft.Colors.with_opacity(0.8, s.CYAN))
            elif index == challenge.answer_index:
                box.bgcolor, box.border = ft.Colors.with_opacity(0.45, s.GREEN), ft.Border.all(2.5, s.GREEN)
            elif index == choice:
                box.bgcolor, box.border = ft.Colors.with_opacity(0.45, "#FF4D4D"), ft.Border.all(2.5, "#FF4D4D")
            else:
                box.bgcolor, box.border = ft.Colors.with_opacity(0.25, "#3A1C8C"), ft.Border.all(1, s.GLASS_BORDER)
            box.ink = not answered
            box.disabled = answered

        correct = answered and challenge.is_correct(choice)  # type: ignore[arg-type]
        self.feedback_box.visible = answered
        if answered:
            self.feedback_switcher.content = self._celebration(correct)
        self.continue_button.visible = answered
        other = self.game.players[1 - self.game.turn]
        label = "Continuar jogando" if correct else f"Passar a vez para {other}"
        row = self.continue_button.content
        row.controls[1].value = label.upper()

        # Painel da esquerda: imagem → lousa (se aberta) → comemoração/correção.
        # A lousa serve para a conta antes da resposta; depois dá lugar à correção.
        visible = self.challenge_board_visible and not answered
        self.challenge_board.panel.visible = visible
        self.image_panel.visible = not visible and not answered
        self.board_button.visible = not answered
        self.board_button.content = "Fechar lousa" if visible else "Abrir lousa"
        self.board_button.icon = ft.Icons.CLOSE_ROUNDED if visible else ft.Icons.DRAW_ROUNDED

    def _answer_challenge(self, event: Any) -> None:
        challenge = self.challenge
        if challenge is None or self.challenge_choice is not None:
            return
        self.challenge_choice = int(event.control.data)
        if challenge.is_correct(self.challenge_choice):
            self.challenge_feedback = self.challenges.encourage(self.game.rng)
            self.sounds.play("incentivo")
        else:
            self.challenge_feedback = f"Quase! A resposta certa é {challenge.answer}.\n{challenge.explanation}"
            self.sounds.play("erro")
        self._apply_challenge_state()
        self.page.update()

    def _toggle_challenge_board(self, _: Any = None) -> None:
        self.challenge_board_visible = not self.challenge_board_visible
        self._apply_challenge_state()
        self.page.update()

    def _close_challenge(self, _: Any = None) -> None:
        challenge, choice = self.challenge, self.challenge_choice
        if challenge is None or choice is None:
            return
        correct = challenge.is_correct(choice)
        self.game.answer_challenge(correct)
        self.challenge = None
        self.challenge_board = None
        self.overlay.visible = False
        self._refresh_stats()
        if not correct:
            self._snack(f"Agora é a vez de {self.game.current_player}!")
        self.seen_turn = self.game.turn
        self.page.update()
        self._notify()

    # ------------------------------------------------------- partida online
    def _notify(self) -> None:
        if self.online is not None:
            self.online.changed()

    def sync(self) -> None:
        """Partida online: o adversário jogou. Redesenha com o estado atual."""

        game = self.game
        for index in range(len(self.cards)):
            self._refresh_card(index)
        self._refresh_stats()
        if len(game.learned) != self.seen_learned:
            self.seen_learned = len(game.learned)
            self.last_concept = game.learned[-1] if game.learned else None
            self.tip_switcher.content = self._tip_content(self.last_concept)
            self._refresh_learned()
        if game.active and not game.is_complete:
            mine = self.online is not None and game.turn == self.online.seat
            if game.awaiting_challenge and not mine:
                self._snack(f"{game.current_player} está no Desafio Relâmpago...")
            elif mine and game.turn != self.seen_turn:
                self._snack("Sua vez! 🎯")
        self.seen_turn = game.turn
        self.page.update()
        if game.is_complete and not self.result_shown:
            self._show_result()
            self.page.update()

    def opponent_left(self, nickname: str) -> None:
        """Partida online: o adversário fechou o jogo ou voltou para a sala."""

        if self.result_shown:
            return
        self.stop()
        self._dialog(
            "Partida encerrada",
            ft.Text(f"{nickname} saiu da partida.", color=s.WHITE),
            [("Voltar à sala", self.on_home, True)],
        )
        self.page.update()

    # ------------------------------------------------------------ diálogos
    def _snack(self, message: str) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                ft.Text(message, color=s.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor="#E6FF3D8B",
                behavior=ft.SnackBarBehavior.FLOATING,
                duration=1600,
            )
        )

    def _dialog(self, title: str, body: ft.Control, actions: list[tuple[str, Callable[[], None] | None, bool]]) -> None:
        def run(action: Callable[[], None] | None) -> Callable[[Any], None]:
            def handler(_: Any) -> None:
                self.page.pop_dialog()
                if action is not None:
                    action()

            return handler

        buttons: list[ft.Control] = []
        for label, action, primary in actions:
            if primary:
                buttons.append(
                    ft.Button(
                        label,
                        on_click=run(action),
                        style=ft.ButtonStyle(bgcolor=s.PINK, color=s.WHITE, shape=ft.RoundedRectangleBorder(radius=14)),
                    )
                )
            else:
                buttons.append(ft.TextButton(label, on_click=run(action), style=ft.ButtonStyle(color=s.CYAN)))
        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                bgcolor="#2A1A5E",
                title=ft.Text(title, weight=ft.FontWeight.W_900, color=s.WHITE),
                # scrollable (e não uma Column com rolagem): a janela fica do
                # tamanho do conteúdo e só rola se não couber na tela.
                content=body,
                scrollable=True,
                actions=buttons,
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _show_result(self) -> None:
        self.result_shown = True
        self.sounds.play("vitoria")
        game = self.game
        lines: list[ft.Control] = []
        if game.mode is Mode.SOLO:
            minutes, seconds = divmod(game.elapsed, 60)
            lines += [
                ft.Text("⭐" * game.stars + "☆" * (3 - game.stars), size=34),
                ft.Text(game.winner_text(), size=16, color=s.WHITE, weight=ft.FontWeight.BOLD),
                ft.Text(f"{game.moves} jogadas • {minutes}:{seconds:02d}", size=14, color=s.MUTED),
            ]
            if game.stars < 3:
                lines.append(ft.Text(f"Dica: com até {game.pairs + 4} jogadas você ganha 3 estrelas!", size=13, color=s.YELLOW))
        else:
            lines += [
                ft.Text("🏆", size=40),
                ft.Text(game.winner_text(), size=18, color=s.WHITE, weight=ft.FontWeight.BOLD),
                ft.Text(f"{game.players[0]} {game.scores[0]} × {game.scores[1]} {game.players[1]}", size=14, color=s.MUTED),
            ]
            desafios = " • ".join(
                f"{name}: {right}/{total}" for name, (right, total) in zip(game.players, game.challenge_stats)
            )
            lines.append(ft.Text(f"⚡ Desafios certos — {desafios}", size=13, color=s.YELLOW))
        lines.append(ft.Text(f"Você descobriu {game.pairs} conceitos de educação financeira. 💡", size=13, color=s.MUTED))
        actions: list[tuple[str, Callable[[], None] | None, bool]] = [
            ("Início", self.on_home, False),
            ("Jogar de novo", self._new_round, True),
        ]
        if self.online is not None:
            actions = [("Voltar à sala", self.on_home, True)]
        self._dialog(
            "Mandou bem! 🎉",
            ft.Column(lines, spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions,
        )

    def _confirm_home(self, _: Any = None) -> None:
        if not self.game.active or not self.game.moves:
            self.on_home()
            return
        self._dialog(
            "Voltar ao início?",
            ft.Text("A partida atual será encerrada.", color=s.WHITE),
            [("Continuar jogando", None, False), ("Voltar", self.on_home, True)],
        )

    def _restart(self, _: Any = None) -> None:
        if not self.game.active or not self.game.moves:
            self._new_round()
            return
        self._dialog(
            "Começar de novo?",
            ft.Text("As cartas serão embaralhadas e a contagem volta a zero.", color=s.WHITE),
            [("Continuar jogando", None, False), ("Nova partida", self._new_round, True)],
        )

    def _new_round(self) -> None:
        self.stop()
        self.game.restart()
        self.last_concept = None
        self.show()
