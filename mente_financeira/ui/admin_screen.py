"""Painel do professor (modo administrador).

Três abas para conferir o conteúdo sem jogar:
- Conceitos do Nível 1 (imagem, "Você sabia?" e "Na prática"), na ordem do banco;
- Desafios Relâmpago de cada tipo, já com gabarito e explicação;
- Todas as questões do Nível 2, fase por fase, com resolução e explicação.
"""

from __future__ import annotations

from collections.abc import Callable
import random
from typing import Any

import flet as ft

from mente_financeira.content import Track
from mente_financeira.content.memory_deck import MemoryDeck
from mente_financeira.core.percent_challenge import KINDS, Challenge
from mente_financeira.ui import style as s
from mente_financeira.ui.layout import Layout, layout_for

CONCEPTS, CHALLENGES, LEVEL2 = "conceitos", "desafios", "nivel2"
TABS = (
    (CONCEPTS, "Conceitos (Nível 1)", ft.Icons.STYLE_ROUNDED),
    (CHALLENGES, "Desafios Relâmpago", ft.Icons.BOLT_ROUNDED),
    (LEVEL2, "Questões (Nível 2)", ft.Icons.CALCULATE_ROUNDED),
)
KIND_LABELS = {
    "_percent_of": "Mesada (x% de…)",
    "_discount": "Desconto",
    "_increase": "Aumento",
    "_what_percent": "Quantos por cento",
}


class AdminScreen:
    def __init__(
        self,
        page: ft.Page,
        deck: MemoryDeck,
        track: Track,
        *,
        on_home: Callable[[], None],
        rng: random.Random | None = None,
    ) -> None:
        self.page = page
        self.deck = deck
        self.track = track
        self.on_home = on_home
        self.rng = rng or random.Random()
        self.layout = layout_for(page.width)
        self.tab = CONCEPTS
        self.concept_index = 0
        self.kind_index = 0
        self.challenge: Challenge = KINDS[0](self.rng)
        self.phase_index = 0

    # ------------------------------------------------------------ ciclo
    def show(self) -> None:
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = s.BG_TOP
        self.page.controls.clear()
        self.page.add(self.build())
        self.page.update()

    def stop(self) -> None:
        pass

    def on_resize(self, event: Any) -> None:
        new_layout = layout_for(getattr(event, "width", None) or self.page.width)
        if new_layout is not self.layout:
            self.layout = new_layout
            self.show()

    @property
    def compact(self) -> bool:
        return self.layout is Layout.COMPACT

    # ------------------------------------------------------------ desenho
    def build(self) -> ft.Control:
        tabs = ft.Row(
            [self._tab_button(key, label, icon) for key, label, icon in TABS],
            spacing=8,
            wrap=True,
            run_spacing=8,
        )
        content = {CONCEPTS: self._concepts, CHALLENGES: self._challenges, LEVEL2: self._level2}[self.tab]()
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                gradient=s.background(),
                padding=12 if self.compact else 24,
                content=ft.Column(
                    [
                        s.admin_banner(
                            "Painel do professor: confira o conteúdo e os gabaritos sem jogar.",
                            [
                                ft.TextButton(
                                    "Início",
                                    icon=ft.Icons.HOME_ROUNDED,
                                    on_click=lambda _: self.on_home(),
                                    style=ft.ButtonStyle(color="#2B1A00"),
                                )
                            ],
                        ),
                        s.gradient_text("PAINEL DO PROFESSOR", 24 if self.compact else 32, [s.YELLOW, s.PINK]),
                        tabs,
                        content,
                    ],
                    spacing=16,
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ),
        )

    def _tab_button(self, key: str, label: str, icon: ft.IconData) -> ft.Container:
        selected = key == self.tab
        return ft.Container(
            data=key,
            on_click=self._select_tab,
            ink=True,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=24,
            bgcolor=ft.Colors.with_opacity(0.3 if selected else 0.08, s.CYAN if selected else s.WHITE),
            border=ft.Border.all(2 if selected else 1, s.CYAN if selected else s.GLASS_BORDER),
            content=ft.Row(
                [
                    ft.Icon(icon, color=s.WHITE, size=18),
                    ft.Text(label, size=14, weight=ft.FontWeight.BOLD, color=s.WHITE),
                ],
                spacing=8,
                tight=True,
            ),
        )

    # -------------------------------------------------------- Conceitos
    def _concepts(self) -> ft.Control:
        concepts = self.deck.concepts
        concept = concepts[self.concept_index]
        navigation = ft.Row(
            [
                ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED, icon_color=s.WHITE, tooltip="Anterior", on_click=self._previous_concept),
                ft.Dropdown(
                    value=concept.id,
                    width=280,
                    dense=True,
                    border_radius=12,
                    color=s.WHITE,
                    options=[ft.DropdownOption(key=c.id, text=f"{i + 1}. {c.name}") for i, c in enumerate(concepts)],
                    on_select=self._choose_concept,
                ),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED, icon_color=s.WHITE, tooltip="Próximo", on_click=self._next_concept),
                ft.Text(f"{self.concept_index + 1}/{len(concepts)}", size=16, weight=ft.FontWeight.BOLD, color=s.YELLOW),
            ],
            wrap=True,
        )
        image = ft.Container(
            width=180 if self.compact else 240,
            height=180 if self.compact else 240,
            border_radius=36,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Image(src=concept.image, fit=ft.BoxFit.COVER),
        )
        details = ft.Column(
            [
                ft.Text(concept.name, size=26 if self.compact else 34, weight=ft.FontWeight.W_900, color=s.WHITE),
                ft.Text("💡 VOCÊ SABIA?", size=13, weight=ft.FontWeight.W_900, color=s.YELLOW),
                ft.Text(concept.tip, size=17, color=s.WHITE),
                ft.Text("📌 NA PRÁTICA", size=13, weight=ft.FontWeight.W_900, color=s.YELLOW),
                ft.Text(concept.example, size=17, color=s.WHITE),
                ft.Text(f"Arquivo: assets/{concept.image} • cor {concept.color} • id {concept.id}", size=12, color=s.MUTED),
            ],
            spacing=8,
            tight=True,
            expand=not self.compact,
        )
        body: ft.Control = (
            ft.Column([ft.Row([image], alignment=ft.MainAxisAlignment.CENTER), details], spacing=16)
            if self.compact
            else ft.Row([image, details], spacing=28, vertical_alignment=ft.CrossAxisAlignment.START)
        )
        note = ft.Text(
            f"Em cada partida são sorteados {self.deck.pairs} dos {len(concepts)} conceitos. "
            "Para editar os textos: mente_financeira/content/memoria.toml.",
            size=12,
            color=s.MUTED,
        )
        return s.glass(ft.Column([navigation, body, note], spacing=18, tight=True), padding=20)

    def _set_concept(self, index: int) -> None:
        self.concept_index = index % len(self.deck.concepts)
        self.show()

    def _previous_concept(self, _: Any = None) -> None:
        self._set_concept(self.concept_index - 1)

    def _next_concept(self, _: Any = None) -> None:
        self._set_concept(self.concept_index + 1)

    def _choose_concept(self, event: Any) -> None:
        ids = [c.id for c in self.deck.concepts]
        value = str(event.control.value)
        if value in ids:
            self._set_concept(ids.index(value))

    # ------------------------------------------------ Desafios Relâmpago
    def _challenges(self) -> ft.Control:
        challenge = self.challenge
        kind_chips = ft.Row(
            [
                ft.Container(
                    data=index,
                    on_click=self._choose_kind,
                    ink=True,
                    padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                    border_radius=20,
                    bgcolor=ft.Colors.with_opacity(0.3 if index == self.kind_index else 0.08, s.YELLOW),
                    border=ft.Border.all(1, s.YELLOW if index == self.kind_index else s.GLASS_BORDER),
                    content=ft.Text(KIND_LABELS[kind.__name__], size=13, weight=ft.FontWeight.BOLD, color=s.WHITE),
                )
                for index, kind in enumerate(KINDS)
            ],
            spacing=8,
            wrap=True,
            run_spacing=8,
        )
        options = [
            ft.Container(
                padding=14,
                border_radius=16,
                bgcolor=ft.Colors.with_opacity(0.3 if i == challenge.answer_index else 0.08, s.GREEN if i == challenge.answer_index else s.WHITE),
                border=ft.Border.all(2 if i == challenge.answer_index else 1, s.GREEN if i == challenge.answer_index else s.GLASS_BORDER),
                content=ft.Row(
                    [
                        ft.Text(f"{'ABCD'[i]})", size=16, weight=ft.FontWeight.W_900, color=s.YELLOW),
                        ft.Text(option, size=18, weight=ft.FontWeight.W_900, color=s.WHITE, expand=True),
                        *([ft.Text("✓ GABARITO", size=13, weight=ft.FontWeight.W_900, color=s.GREEN)] if i == challenge.answer_index else []),
                    ],
                    spacing=10,
                ),
            )
            for i, option in enumerate(challenge.options)
        ]
        return s.glass(
            ft.Column(
                [
                    ft.Text("Tipo de pergunta:", size=13, color=s.MUTED),
                    kind_chips,
                    ft.Row(
                        [
                            ft.Container(
                                width=110,
                                height=110,
                                border_radius=22,
                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                content=ft.Image(src=challenge.image, fit=ft.BoxFit.CONTAIN),
                            ),
                            ft.Column(
                                [
                                    ft.Text(challenge.label, size=14, weight=ft.FontWeight.W_900, color=s.YELLOW),
                                    ft.Text(challenge.item, size=20, weight=ft.FontWeight.W_700, color=s.CYAN),
                                    ft.Text(f"Imagem: assets/{challenge.image}", size=12, color=s.MUTED),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                        ],
                        spacing=16,
                    ),
                    ft.Text(challenge.question, size=22, weight=ft.FontWeight.W_700, color=s.WHITE),
                    *options,
                    ft.Container(
                        padding=14,
                        border_radius=16,
                        bgcolor=ft.Colors.with_opacity(0.14, s.CYAN),
                        content=ft.Column(
                            [
                                ft.Text("📝 EXPLICAÇÃO MOSTRADA A QUEM ERRA", size=13, weight=ft.FontWeight.W_900, color=s.CYAN),
                                ft.Text(challenge.explanation, size=16, color=s.WHITE),
                            ],
                            spacing=6,
                            tight=True,
                        ),
                    ),
                    ft.Row(
                        [s.pill_button("GERAR OUTRO DESAFIO", ft.Icons.AUTORENEW_ROUNDED, self._new_challenge, height=52)],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Text(
                        "Os valores são sorteados a cada desafio. As alternativas erradas imitam erros comuns.",
                        size=12,
                        color=s.MUTED,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            padding=20,
        )

    def _choose_kind(self, event: Any) -> None:
        self.kind_index = int(event.control.data)
        self._new_challenge()

    def _new_challenge(self, _: Any = None) -> None:
        self.challenge = KINDS[self.kind_index](self.rng)
        self.show()

    # ------------------------------------------------------------ Nível 2
    def _level2(self) -> ft.Control:
        phase = self.track.phases[self.phase_index]
        selector = ft.Dropdown(
            value=str(self.phase_index),
            width=420 if not self.compact else None,
            dense=True,
            border_radius=12,
            color=s.WHITE,
            options=[ft.DropdownOption(key=str(i), text=p.title) for i, p in enumerate(self.track.phases)],
            on_select=self._choose_phase,
        )
        cards = [
            s.glass(
                ft.Column(
                    [
                        ft.Text(f"CENÁRIO {n}  •  {pair.pair_id}", size=12, weight=ft.FontWeight.BOLD, color=s.MUTED),
                        ft.Text(pair.question, size=17, weight=ft.FontWeight.W_600, color=s.WHITE),
                        ft.Text(f"✓ {pair.resolution}", size=17, weight=ft.FontWeight.W_900, color=s.GREEN),
                        ft.Text(pair.explanation, size=14, color=s.MUTED),
                    ],
                    spacing=6,
                    tight=True,
                ),
                padding=16,
            )
            for n, pair in enumerate((phase.render(scenario) for scenario in phase.scenarios), start=1)
        ]
        return ft.Column(
            [
                ft.Row([selector], wrap=True),
                ft.Text(
                    f"{phase.objective}  Cada partida sorteia {self.track.pairs_per_phase} dos "
                    f"{len(phase.scenarios)} cenários desta fase.",
                    size=14,
                    color=s.MUTED,
                ),
                *cards,
            ],
            spacing=12,
            tight=True,
        )

    def _choose_phase(self, event: Any) -> None:
        self.phase_index = int(event.control.value)
        self.show()

    # ------------------------------------------------------------ abas
    def _select_tab(self, event: Any) -> None:
        self.tab = event.control.data
        self.show()
