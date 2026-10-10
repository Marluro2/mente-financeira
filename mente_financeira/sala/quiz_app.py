"""Telas do Quiz ao vivo: a do notebook (telão) e a do celular de cada pessoa.

O notebook abre ``/?quiz=apresentar`` e mostra o QR code, as perguntas, o
relógio e o placar. Quem escaneia o QR code abre ``/?quiz=jogar``, escolhe um
apelido e responde pelo celular. Todas as sessões olham para o mesmo ``Quiz``
na memória do servidor e se avisam pelo ``pubsub`` do Flet (tópico ``quiz``).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import parse_qs, urlparse

import flet as ft

from mente_financeira.sala.app import ROOM_TRACKS, Messenger, SessionStore
from mente_financeira.sala.quiz import Phase, Quiz, QuizError
from mente_financeira.sala.salas import NICKNAME_MAX, NicknameError
from mente_financeira.sugestoes import Suggestion
from mente_financeira.ui import style as s
from mente_financeira.ui.shell import MEMORY_TRACKS
from mente_financeira.ui.sounds import SoundEffects
from mente_financeira.ui.suggestion_form import SuggestionForm, suggestion_button, suggestion_qr
from mente_financeira.ui.tracks import FUNDAMENTAL

QUIZ_TOPIC = "quiz"
PRESENT, PLAY = "apresentar", "jogar"  # ?quiz=apresentar (notebook) e ?quiz=jogar (celular)
QUIZ_QR_PATH = "/qr/quiz.png"  # desenhado pelo servidor, aponta para ?quiz=jogar
CLOCK_STEP_SECONDS = 0.25
LOCAL_IPS = ("127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost")

LETTERS = "ABCD"
OPTION_COLORS = ("#E0306F", "#1F6FE0", "#D98200", "#14A06E")
MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
DARK_TEXT = "#0B1E3F"


def new_quiz() -> Quiz:
    return Quiz({t.key: MEMORY_TRACKS[t.key][1] for t in ROOM_TRACKS}, FUNDAMENTAL)


def quiz_role(route: str | None) -> str | None:
    """``apresentar``, ``jogar`` ou None (endereço sem ``?quiz=``)."""

    values = parse_qs(urlparse(route or "").query).get("quiz")
    if not values:
        return None
    return PRESENT if values[0].strip().lower() == PRESENT else PLAY


def is_local(client_ip: str | None, own_ips: Iterable[str] = ()) -> bool:
    """O telão só abre no próprio notebook, para ninguém assumir o quiz pelo celular.

    ``own_ips``: endereços do notebook na rede (quando ele abre pelo IP, e não por localhost).
    """

    return (client_ip or "") in {*LOCAL_IPS, *own_ips}


def points_text(points: int) -> str:
    return f"{points:,}".replace(",", ".")


def track_title(key: str) -> str:
    return next(t.title for t in ROOM_TRACKS if t.key == key)


def _letter(index: int, *, size: float = 40) -> ft.Container:
    return ft.Container(
        width=size,
        height=size,
        border_radius=size / 2,
        bgcolor=ft.Colors.with_opacity(0.28, s.WHITE),
        alignment=ft.Alignment.CENTER,
        content=ft.Text(LETTERS[index], size=size * 0.5, weight=ft.FontWeight.W_900, color=s.WHITE),
    )


class QuizScreen:
    """Base das duas telas: desenho do fundo e recados entre as sessões."""

    title = "Mente Financeira • Quiz ao vivo"

    def __init__(self, page: ft.Page, quiz: Quiz, messenger: Messenger, *, session_id: str) -> None:
        self.page = page
        self.quiz = quiz
        self.messenger = messenger
        self.session_id = session_id
        self.generation = 0  # muda a cada desenho: o relógio antigo para
        self.sounds = SoundEffects(page, SessionStore())
        self.sounds.preload()
        self.page.title = self.title
        self.page.padding = 0
        self.page.spacing = 0
        messenger.subscribe(QUIZ_TOPIC, self._on_message)

    @property
    def width(self) -> float:
        return self.page.width or 400

    def broadcast(self, what: str) -> None:
        """Avisa todas as telas (inclusive esta). ``what``: phase, players, lobby ou answers."""

        self.messenger.send(QUIZ_TOPIC, {"kind": QUIZ_TOPIC, "what": what})

    async def _on_message(self, message: dict[str, Any]) -> None:
        raise NotImplementedError

    def show(self) -> None:
        raise NotImplementedError

    def close(self, _: Any = None) -> None:
        self.generation += 1
        self.messenger.close()

    def _fill(self, content: ft.Control) -> None:
        self.page.on_resize = None
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = s.BG_TOP
        self.page.controls.clear()
        self.page.add(
            ft.SafeArea(
                expand=True,
                content=ft.Container(
                    expand=True,
                    gradient=s.background(),
                    content=ft.Column(
                        [content],
                        scroll=ft.ScrollMode.AUTO,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            )
        )
        self.page.update()

    def _quiz_chip(self) -> ft.Control:
        return s.chip("QUIZ AO VIVO", icon=ft.Icons.QUIZ_ROUNDED, color=s.YELLOW, size=12)


# ====================================================================== telão
class QuizHost(QuizScreen):
    """Tela do notebook (ligada no telão ou virada para o público)."""

    def __init__(self, page: ft.Page, quiz: Quiz, messenger: Messenger, *, session_id: str, join_url: str = "") -> None:
        super().__init__(page, quiz, messenger, session_id=session_id)
        self.join_url = join_url  # endereço escrito embaixo do QR code
        self.answered_text = ft.Text()
        self.countdown_text = ft.Text()
        self.countdown_ring = ft.ProgressRing()
        self.error_text = ft.Text()
        self.cheered = False
        self.show()

    async def _on_message(self, message: dict[str, Any]) -> None:
        if message.get("what") == "answers" and self.quiz.phase is Phase.QUESTION:
            self.answered_text.value = self._answered_label()
            self.page.update()
            return
        self.show()

    def _on_resize(self, _: Any = None) -> None:
        self.show()

    # ------------------------------------------------------------ ações
    def _choose_track(self, event: Any) -> None:
        self.quiz.choose_track(event.control.data)
        self.broadcast("lobby")

    def _start(self, _: Any = None) -> None:
        try:
            self.quiz.start()
        except QuizError as error:
            self.error_text.value = str(error)
            self.error_text.visible = True
            self.page.update()
            return
        self.broadcast("phase")

    def _reveal(self, _: Any = None) -> None:
        if self.quiz.reveal(self.quiz.number):
            self.broadcast("phase")

    def _next(self, _: Any = None) -> None:
        if self.quiz.advance(self.quiz.number):
            self.broadcast("phase")

    def _restart(self, _: Any = None) -> None:
        self.quiz.restart()
        self.broadcast("phase")

    async def _clock(self, generation: int, number: int) -> None:
        """Atualiza o relógio e mostra a resposta quando o tempo acaba."""

        shown = self.quiz.remaining()
        while generation == self.generation and self.quiz.phase is Phase.QUESTION and self.quiz.number == number:
            await asyncio.sleep(CLOCK_STEP_SECONDS)
            if generation != self.generation:
                return
            if self.quiz.time_up:
                if self.quiz.reveal(number):
                    self.broadcast("phase")
                return
            left = self.quiz.remaining()
            if left != shown:
                shown = left
                self._set_countdown(left)
                self.page.update()

    # ------------------------------------------------------------ desenho
    def show(self) -> None:
        self.generation += 1
        phase = self.quiz.phase
        if phase is Phase.LOBBY:
            view = self._lobby()
        elif phase is Phase.QUESTION:
            view = self._question()
        elif phase is Phase.REVEAL:
            view = self._reveal_view()
        else:
            view = self._podium()
            if not self.cheered:
                self.sounds.play("vitoria")
        self.cheered = phase is Phase.FINISHED  # a vinheta do pódio toca uma vez só
        self._fill(ft.Container(width=min(1400, self.width), padding=ft.Padding.symmetric(horizontal=28, vertical=22), content=view))
        self.page.on_resize = self._on_resize
        if phase is Phase.QUESTION:
            self.page.run_task(self._clock, self.generation, self.quiz.number)

    @property
    def wide(self) -> bool:
        return self.width >= 900

    def _side_by_side(self, first: ft.Control, second: ft.Control, *, ratio: tuple[int, int] = (1, 1)) -> ft.Control:
        if not self.wide:
            return ft.Column([first, second], spacing=22, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        first.expand, second.expand = ratio
        return ft.Row([first, second], spacing=28, vertical_alignment=ft.CrossAxisAlignment.START)

    def _heading(self, text: str, size: float = 22) -> ft.Text:
        return ft.Text(text, size=size, weight=ft.FontWeight.W_900, color=s.WHITE)

    def _top_bar(self, *chips: ft.Control, trailing: list[ft.Control] | None = None) -> ft.Control:
        return ft.Row(
            [self._quiz_chip(), *chips, ft.Container(expand=True), *(trailing or [])],
            spacing=10,
            wrap=not self.wide,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _end_button(self) -> ft.Control:
        return ft.TextButton("Encerrar quiz", icon=ft.Icons.STOP_CIRCLE_OUTLINED, on_click=self._restart, style=ft.ButtonStyle(color=s.MUTED))

    # ---- sala de espera
    def _track_tile(self, track: Any) -> ft.Container:
        selected = track.key == self.quiz.track
        first, second = track.colors
        look: dict[str, Any] = (
            {"gradient": ft.LinearGradient(colors=[first, second]), "border": ft.Border.all(2, s.WHITE)}
            if selected
            else {"bgcolor": ft.Colors.with_opacity(0.10, first), "border": ft.Border.all(1.5, ft.Colors.with_opacity(0.55, first))}
        )
        return ft.Container(
            data=track.key,
            on_click=self._choose_track,
            ink=True,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border_radius=18,
            content=ft.Row(
                [
                    ft.Icon(track.icon, color=s.WHITE, size=26),
                    ft.Text(track.title, size=16, weight=ft.FontWeight.W_900, color=s.WHITE, expand=True),
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED if selected else ft.Icons.RADIO_BUTTON_UNCHECKED, color=s.WHITE),
                ],
                spacing=12,
            ),
            **look,
        )

    def _lobby(self) -> ft.Control:
        qr_size = 300 if self.wide else 220
        join = ft.Column(
            [
                s.gradient_text("QUIZ AO VIVO", 54 if self.wide else 40, [s.YELLOW, s.ORANGE, s.PINK]),
                s.gradient_text("MENTE FINANCEIRA", 26 if self.wide else 20, [s.CYAN, "#8F88FF", s.PINK]),
                ft.Container(
                    padding=14,
                    border_radius=26,
                    bgcolor=s.WHITE,
                    content=ft.Image(src=QUIZ_QR_PATH, width=qr_size, height=qr_size, semantics_label="QR code para entrar no quiz"),
                ),
                ft.Text("Escaneie com a câmera do celular", size=20, weight=ft.FontWeight.W_800, color=s.WHITE),
                *([ft.Text(f"ou abra {self.join_url}", size=16, color=s.CYAN, selectable=True)] if self.join_url else []),
                ft.Text("1. Conecte no Wi-Fi do estande   2. Escaneie o QR code   3. Escolha um apelido", size=14, color=s.MUTED, text_align=ft.TextAlign.CENTER),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        players = self.quiz.ranking()
        names: ft.Control = (
            ft.Row([s.chip(p.nickname, icon=ft.Icons.PERSON_ROUNDED, color=s.CYAN, size=15) for p in players], wrap=True, spacing=8, run_spacing=8)
            if players
            else ft.Text("Ninguém entrou ainda. Escaneie o QR code!", size=16, color=s.MUTED)
        )
        self.error_text = ft.Text("", size=15, color="#FF6B8B", weight=ft.FontWeight.BOLD, visible=False)
        setup = s.glass(
            ft.Column(
                [
                    self._heading("Trilha das perguntas"),
                    *[self._track_tile(track) for track in ROOM_TRACKS],
                    ft.Container(height=4),
                    self._heading(f"Jogadores: {len(players)}"),
                    names,
                    ft.Container(height=4),
                    self.error_text,
                    s.pill_button("COMEÇAR O QUIZ", ft.Icons.PLAY_ARROW_ROUNDED, self._start, height=60),
                    ft.Text(
                        f"{self.quiz.count} perguntas • {self.quiz.seconds} segundos cada • quem acerta mais rápido ganha mais pontos",
                        size=14,
                        color=s.MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=22,
            radius=28,
        )
        return self._side_by_side(join, setup)

    # ---- pergunta
    def _answered_label(self) -> str:
        return f"{self.quiz.answered} de {len(self.quiz.players)} responderam"

    def _set_countdown(self, left: int) -> None:
        self.countdown_text.value = str(left)
        self.countdown_ring.value = left / self.quiz.seconds
        self.countdown_ring.color = "#FF4D6D" if left <= 5 else s.YELLOW

    def _countdown(self) -> ft.Control:
        size = 92
        self.countdown_ring = ft.ProgressRing(width=size, height=size, stroke_width=9, bgcolor=ft.Colors.with_opacity(0.15, s.WHITE))
        self.countdown_text = ft.Text("", size=34, weight=ft.FontWeight.W_900, color=s.WHITE)
        self._set_countdown(self.quiz.remaining())
        return ft.Stack(
            [self.countdown_ring, ft.Container(width=size, height=size, alignment=ft.Alignment.CENTER, content=self.countdown_text)],
            width=size,
            height=size,
        )

    def _question_card(self, *, size: float) -> ft.Control:
        question = self.quiz.question
        assert question is not None
        text = ft.Column(
            [
                ft.Row([s.chip(question.label or "DESAFIO RELÂMPAGO", icon=ft.Icons.BOLT_ROUNDED, color=s.ORANGE, size=13)]),
                ft.Text(question.question, size=size, weight=ft.FontWeight.W_800, color=s.WHITE),
            ],
            spacing=10,
            expand=True,
        )
        image = (
            [ft.Image(src=question.image, width=size * 4.6, height=size * 4.6, fit=ft.BoxFit.CONTAIN)]
            if question.image and self.wide
            else []
        )
        return s.glass(ft.Row([*image, text], spacing=22, vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=22, radius=28)

    def _option(self, index: int, text: str) -> ft.Container:
        return ft.Container(
            expand=True,
            height=92 if self.wide else 70,
            padding=ft.Padding.symmetric(horizontal=18, vertical=10),
            border_radius=22,
            bgcolor=OPTION_COLORS[index],
            shadow=ft.BoxShadow(blur_radius=18, color=ft.Colors.with_opacity(0.45, OPTION_COLORS[index]), offset=ft.Offset(0, 6)),
            content=ft.Row(
                [_letter(index, size=48 if self.wide else 38), ft.Text(text, size=28 if self.wide else 20, weight=ft.FontWeight.W_900, color=s.WHITE, expand=True)],
                spacing=16,
            ),
        )

    def _question(self) -> ft.Control:
        question = self.quiz.question
        assert question is not None
        self.answered_text = ft.Text(self._answered_label(), size=18, weight=ft.FontWeight.BOLD, color=s.CYAN)
        options = [self._option(i, text) for i, text in enumerate(question.options)]
        rows = [ft.Row(options[i : i + 2], spacing=16) for i in range(0, len(options), 2)]
        return ft.Column(
            [
                self._top_bar(
                    s.chip(f"PERGUNTA {self.quiz.number} DE {self.quiz.total}", color=s.CYAN, size=14),
                    s.chip(track_title(self.quiz.track), color=s.PINK, size=14),
                    trailing=[self.answered_text, self._countdown()],
                ),
                self._question_card(size=32 if self.wide else 22),
                *rows,
                ft.Row(
                    [
                        ft.TextButton("Mostrar a resposta agora", icon=ft.Icons.VISIBILITY_ROUNDED, on_click=self._reveal, style=ft.ButtonStyle(color=s.CYAN)),
                        self._end_button(),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    # ---- resposta
    def _result_option(self, index: int, text: str, votes: int, most: int) -> ft.Control:
        question = self.quiz.question
        assert question is not None
        right = question.is_correct(index)
        bar = ft.Container(
            height=10,
            border_radius=5,
            bgcolor=s.GREEN if right else ft.Colors.with_opacity(0.6, s.WHITE),
            width=max(6, 240 * votes / most) if most else 6,
        )
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=20,
            bgcolor=OPTION_COLORS[index] if right else ft.Colors.with_opacity(0.30, OPTION_COLORS[index]),
            border=ft.Border.all(3, s.GREEN) if right else None,
            opacity=1 if right else 0.65,
            content=ft.Row(
                [
                    _letter(index, size=40),
                    ft.Column(
                        [ft.Text(text, size=22, weight=ft.FontWeight.W_900, color=s.WHITE), bar],
                        spacing=6,
                        expand=True,
                        tight=True,
                    ),
                    ft.Text(str(votes), size=24, weight=ft.FontWeight.W_900, color=s.WHITE),
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED if right else ft.Icons.CLOSE_ROUNDED, color=s.WHITE, size=30),
                ],
                spacing=14,
            ),
        )

    def _leaderboard(self, limit: int = 5) -> ft.Control:
        rows: list[ft.Control] = []
        for player in self.quiz.ranking()[:limit]:
            place = self.quiz.place_of(player.id)
            streak = f"  🔥{player.streak}" if player.streak >= 2 else ""
            rows.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                    border_radius=16,
                    bgcolor=ft.Colors.with_opacity(0.10, s.WHITE),
                    content=ft.Row(
                        [
                            ft.Text(MEDALS.get(place, f"{place}º"), size=22, weight=ft.FontWeight.W_900, color=s.YELLOW, width=42),
                            ft.Text(player.nickname + streak, size=19, weight=ft.FontWeight.W_800, color=s.WHITE, expand=True),
                            ft.Text(points_text(player.score), size=20, weight=ft.FontWeight.W_900, color=s.CYAN),
                        ],
                        spacing=10,
                    ),
                )
            )
        if not rows:
            rows.append(ft.Text("Ninguém no quiz.", color=s.MUTED))
        return s.glass(
            ft.Column([self._heading("PLACAR"), *rows], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            padding=20,
            radius=26,
        )

    def _reveal_view(self) -> ft.Control:
        question = self.quiz.question
        assert question is not None
        votes = self.quiz.distribution()
        right = votes[question.answer_index] if votes else 0
        answer = ft.Column(
            [
                ft.Text(question.question, size=22 if self.wide else 18, weight=ft.FontWeight.W_700, color=s.WHITE),
                *[self._result_option(i, text, votes[i], max(votes)) for i, text in enumerate(question.options)],
                s.glass(
                    ft.Row(
                        [ft.Text("💡", size=26), ft.Text(question.explanation, size=18, color=s.WHITE, expand=True)],
                        spacing=12,
                    ),
                    padding=16,
                    radius=20,
                ),
            ],
            spacing=12,
        )
        last = self.quiz.is_last
        next_button = s.pill_button(
            "VER O PÓDIO" if last else "PRÓXIMA PERGUNTA",
            ft.Icons.EMOJI_EVENTS_ROUNDED if last else ft.Icons.ARROW_FORWARD_ROUNDED,
            self._next,
            height=58,
            colors=[s.GREEN, s.CYAN] if last else None,
        )
        next_button.width = 320
        return ft.Column(
            [
                self._top_bar(
                    s.chip(f"PERGUNTA {self.quiz.number} DE {self.quiz.total}", color=s.CYAN, size=14),
                    s.chip(f"{right} de {len(self.quiz.players)} acertaram", icon=ft.Icons.CHECK_ROUNDED, color=s.GREEN, size=14),
                ),
                self._side_by_side(answer, self._leaderboard(), ratio=(3, 2)),
                ft.Row(
                    [
                        self._end_button(),
                        next_button,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    # ---- pódio
    def _step(self, slot: int, height: float) -> ft.Control:
        """Degrau do pódio: ``slot`` é a posição na fila; o número mostrado respeita empates."""

        ranking = self.quiz.ranking()
        player = ranking[slot - 1] if len(ranking) >= slot else None
        place = self.quiz.place_of(player.id) if player else slot
        colors = {1: [s.YELLOW, s.ORANGE], 2: ["#D9DEE8", "#8E9AB5"], 3: ["#F0A46B", "#B4622D"]}[place]
        return ft.Column(
            [
                ft.Text(MEDALS[place] if player else "", size=40),
                ft.Text(player.nickname if player else "", size=24, weight=ft.FontWeight.W_900, color=s.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text(f"{points_text(player.score)} pts" if player else "", size=18, weight=ft.FontWeight.BOLD, color=s.CYAN),
                ft.Container(
                    width=170 if self.wide else 104,
                    height=height,
                    border_radius=ft.BorderRadius.only(top_left=18, top_right=18),
                    gradient=ft.LinearGradient(begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER, colors=colors),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(f"{place}º", size=40, weight=ft.FontWeight.W_900, color=DARK_TEXT),
                ),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.END,
        )

    def _podium(self) -> ft.Control:
        scale = 1 if self.wide else 0.6
        steps = ft.Row(
            [self._step(2, 140 * scale), self._step(1, 200 * scale), self._step(3, 100 * scale)],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.END,
            spacing=14,
        )
        others = [
            ft.Row(
                [
                    ft.Text(f"{self.quiz.place_of(p.id)}º", size=18, weight=ft.FontWeight.W_900, color=s.YELLOW, width=40),
                    ft.Text(p.nickname, size=18, color=s.WHITE, expand=True),
                    ft.Text(points_text(p.score), size=18, weight=ft.FontWeight.BOLD, color=s.CYAN),
                ]
            )
            for p in self.quiz.ranking()[3:10]
        ]
        board: ft.Control = steps
        if others:
            # No telão, a lista fica ao lado do pódio para tudo caber sem rolar.
            listing = s.glass(ft.Column(others, spacing=6, width=300 if self.wide else min(520, self.width - 80)), padding=16, radius=22)
            board = (
                ft.Row([steps, listing], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.END, spacing=36)
                if self.wide
                else ft.Column([steps, listing], spacing=18, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        again = s.pill_button("NOVO QUIZ", ft.Icons.REPLAY_ROUNDED, self._restart, height=58, colors=[s.CYAN, "#6C63FF"])
        again.width = 280
        return ft.Column(
            [
                self._top_bar(s.chip(track_title(self.quiz.track), color=s.PINK, size=14)),
                ft.Row([s.gradient_text("PÓDIO", 54 if self.wide else 42, [s.YELLOW, s.ORANGE, s.PINK])], alignment=ft.MainAxisAlignment.CENTER),
                board,
                ft.Row([again], alignment=ft.MainAxisAlignment.CENTER),
                ft.Text("Quem está no quiz continua dentro para a próxima rodada.", size=14, color=s.MUTED, text_align=ft.TextAlign.CENTER),
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )


# ==================================================================== celular
class QuizPhone(QuizScreen):
    """Tela de quem joga: apelido, alternativas e resultado de cada pergunta."""

    def __init__(
        self,
        page: ft.Page,
        quiz: Quiz,
        messenger: Messenger,
        *,
        session_id: str,
        on_suggestion: Callable[[Suggestion], None] | None = None,
    ) -> None:
        super().__init__(page, quiz, messenger, session_id=session_id)
        self.on_suggestion = on_suggestion
        self.name_field = ft.TextField()
        self.countdown_text = ft.Text()
        self.sounded: tuple[Phase, int] | None = None  # som do resultado toca uma vez só
        self.show()

    @property
    def player(self) -> Any:
        return self.quiz.players.get(self.session_id)

    async def _on_message(self, message: dict[str, Any]) -> None:
        # Antes de entrar há um campo de texto na tela: redesenhar apagaria o que a pessoa digita.
        if self.player is None:
            return
        what = message.get("what")
        if what == "phase" or (what in ("players", "lobby") and self.quiz.phase is Phase.LOBBY):
            self.show()

    # ------------------------------------------------------------ ações
    def _join(self, _: Any = None) -> None:
        self.name_field.error = None
        try:
            self.quiz.join(self.session_id, self.name_field.value)
        except (NicknameError, QuizError) as error:
            self.name_field.error = str(error)
            self.page.update()
            return
        self.broadcast("players")
        self.show()

    def _answer(self, event: Any) -> None:
        number = self.quiz.number
        if not self.quiz.answer(self.session_id, int(event.control.data)):
            self.show()
            return
        self.sounds.play("virar")
        self.show()
        self.broadcast("answers")
        if self.quiz.all_answered and self.quiz.reveal(number):
            self.broadcast("phase")

    def close(self, _: Any = None) -> None:
        if self.quiz.leave(self.session_id) is not None:
            self.broadcast("players")
        super().close()

    async def _clock(self, generation: int, number: int) -> None:
        shown = self.quiz.remaining()
        while generation == self.generation and self.quiz.phase is Phase.QUESTION and self.quiz.number == number:
            await asyncio.sleep(CLOCK_STEP_SECONDS)
            if generation != self.generation:
                return
            if self.quiz.time_up:
                self.show()  # "Tempo esgotado"
                return
            left = self.quiz.remaining()
            if left != shown:
                shown = left
                self.countdown_text.value = f"{left} s"
                self.page.update()

    # ------------------------------------------------------------ desenho
    def show(self) -> None:
        self.generation += 1
        player = self.player
        phase = self.quiz.phase
        open_question = False
        if player is None:
            items = self._join_items()
        elif phase is Phase.LOBBY:
            items = self._lobby_items()
        elif phase is Phase.QUESTION:
            open_question = player.choice is None and not self.quiz.time_up
            items = self._question_items() if open_question else self._waiting_items()
        elif phase is Phase.REVEAL:
            items = self._result_items()
        else:
            items = self._final_items()
        self._fill(ft.Container(padding=ft.Padding.symmetric(horizontal=12, vertical=20), content=self._panel(items)))
        if open_question:
            self.page.run_task(self._clock, self.generation, self.quiz.number)

    def _panel(self, items: list[ft.Control]) -> ft.Container:
        return ft.Container(
            width=min(540, self.width - 24),
            padding=ft.Padding.symmetric(horizontal=16, vertical=20),
            border_radius=28,
            bgcolor=ft.Colors.with_opacity(0.10, s.WHITE),
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.35, s.YELLOW)),
            shadow=ft.BoxShadow(blur_radius=60, color=ft.Colors.with_opacity(0.35, "#6C63FF")),
            content=ft.Column(items, spacing=14, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        )

    def _center(self, text: str, size: float, *, color: str = s.WHITE, weight: ft.FontWeight = ft.FontWeight.W_900) -> ft.Text:
        return ft.Text(text, size=size, weight=weight, color=color, text_align=ft.TextAlign.CENTER)

    def _title(self) -> ft.Control:
        return ft.Column(
            [
                s.gradient_text("MENTE", 40, [s.YELLOW, s.ORANGE, s.PINK]),
                s.gradient_text("FINANCEIRA", 26, [s.CYAN, "#8F88FF", s.PINK]),
                ft.Row([self._quiz_chip()], alignment=ft.MainAxisAlignment.CENTER),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _status_row(self) -> ft.Control:
        player = self.player
        return ft.Row(
            [
                s.chip(player.nickname if player else "", icon=ft.Icons.PERSON_ROUNDED, color=s.CYAN, size=13),
                s.chip(f"{points_text(player.score if player else 0)} pts", icon=ft.Icons.STARS_ROUNDED, color=s.YELLOW, size=13),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=True,
        )

    def _join_items(self) -> list[ft.Control]:
        self.name_field = ft.TextField(
            value=self.name_field.value,
            label="Seu apelido",
            hint_text="Ex.: Lia, Pedro10",
            max_length=NICKNAME_MAX,
            border_radius=16,
            filled=True,
            bgcolor=ft.Colors.with_opacity(0.10, s.WHITE),
            border_color=s.GLASS_BORDER,
            focused_border_color=s.CYAN,
            color=s.WHITE,
            label_style=ft.TextStyle(color=s.MUTED),
            prefix_icon=ft.Icons.BADGE_OUTLINED,
            on_submit=self._join,
            autofocus=True,
        )
        started = self.quiz.phase is not Phase.LOBBY
        return [
            self._title(),
            self._center(
                "O quiz já começou, mas dá para entrar agora!" if started else "Responda pelo celular as perguntas que aparecem na tela do estande.",
                15,
                weight=ft.FontWeight.W_600,
            ),
            self.name_field,
            s.pill_button("ENTRAR NO QUIZ", ft.Icons.LOGIN_ROUNDED, self._join, height=56),
            self._center("Só pedimos um apelido (não use seu nome completo). Nada fica guardado.", 12, color=s.MUTED, weight=ft.FontWeight.NORMAL),
        ]

    def _lobby_items(self) -> list[ft.Control]:
        player = self.player
        count = len(self.quiz.players)
        return [
            self._title(),
            self._center(f"Você está no quiz, {player.nickname}! 🎉", 22),
            self._center("Olhe para a tela do estande: o quiz começa já já.", 16, weight=ft.FontWeight.W_600),
            ft.Row(
                [ft.ProgressRing(color=s.YELLOW, width=22, height=22, stroke_width=3), ft.Text("Esperando começar...", color=s.CYAN, weight=ft.FontWeight.BOLD)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            self._center(
                f"{count} {'pessoa' if count == 1 else 'pessoas'} no quiz • {track_title(self.quiz.track)}",
                14,
                color=s.MUTED,
                weight=ft.FontWeight.W_600,
            ),
            self._center("Dica: acertar rápido vale mais pontos!", 14, color=s.YELLOW, weight=ft.FontWeight.BOLD),
        ]

    def _question_items(self) -> list[ft.Control]:
        question = self.quiz.question
        assert question is not None
        self.countdown_text = ft.Text(f"{self.quiz.remaining()} s", size=15, weight=ft.FontWeight.W_900, color=s.WHITE)
        timer = ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.2, s.ORANGE),
            border=ft.Border.all(1, s.ORANGE),
            content=ft.Row([ft.Icon(ft.Icons.TIMER_ROUNDED, color=s.ORANGE, size=18), self.countdown_text], spacing=6, tight=True),
        )
        buttons = [
            ft.Container(
                data=index,
                on_click=self._answer,
                ink=True,
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                border_radius=20,
                bgcolor=OPTION_COLORS[index],
                shadow=ft.BoxShadow(blur_radius=14, color=ft.Colors.with_opacity(0.45, OPTION_COLORS[index]), offset=ft.Offset(0, 5)),
                content=ft.Row(
                    [_letter(index, size=38), ft.Text(text, size=19, weight=ft.FontWeight.W_900, color=s.WHITE, expand=True)],
                    spacing=12,
                ),
            )
            for index, text in enumerate(question.options)
        ]
        return [
            ft.Row(
                [s.chip(f"PERGUNTA {self.quiz.number}/{self.quiz.total}", color=s.CYAN, size=13), timer],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Text(question.question, size=17, weight=ft.FontWeight.W_700, color=s.WHITE),
            *buttons,
            self._center("Responda rápido: vale mais pontos!", 13, color=s.YELLOW, weight=ft.FontWeight.BOLD),
        ]

    def _waiting_items(self) -> list[ft.Control]:
        player = self.player
        question = self.quiz.question
        assert question is not None
        if player.choice is None:
            body: list[ft.Control] = [
                self._center("⏰", 56),
                self._center("Tempo esgotado!", 26),
                self._center("Fique de olho na próxima pergunta.", 16, weight=ft.FontWeight.W_600),
            ]
        else:
            badge = ft.Container(padding=6, border_radius=50, bgcolor=OPTION_COLORS[player.choice], content=_letter(player.choice, size=72))
            body = [
                ft.Row([badge], alignment=ft.MainAxisAlignment.CENTER),
                self._center(question.options[player.choice], 22),
                self._center("Resposta enviada! ⏳", 24, color=s.YELLOW),
                self._center("Espere o tempo acabar para ver se acertou.", 16, weight=ft.FontWeight.W_600),
            ]
        return [ft.Row([s.chip(f"PERGUNTA {self.quiz.number}/{self.quiz.total}", color=s.CYAN, size=13)], alignment=ft.MainAxisAlignment.CENTER), *body, self._status_row()]

    def _place_line(self) -> ft.Control:
        player = self.player
        place = self.quiz.place_of(player.id)
        total = len(self.quiz.players)
        lines: list[ft.Control] = [
            self._center(f"{MEDALS.get(place, '')} {place}º lugar".strip(), 30, color=s.YELLOW),
            self._center(f"{points_text(player.score)} pontos • {total} {'pessoa' if total == 1 else 'pessoas'} no quiz", 15, weight=ft.FontWeight.W_600),
        ]
        if player.streak >= 2:
            lines.append(self._center(f"🔥 {player.streak} acertos seguidos!", 16, color=s.ORANGE))
        return s.glass(ft.Column(lines, spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=14, radius=22)

    def _result_items(self) -> list[ft.Control]:
        player = self.player
        question = self.quiz.question
        assert question is not None
        right = player.choice is not None and question.is_correct(player.choice)
        key = (Phase.REVEAL, self.quiz.number)
        if self.sounded != key:
            self.sounded = key
            self.sounds.play("incentivo" if right else "erro")
        answer = f"{LETTERS[question.answer_index]}) {question.answer}"
        if right:
            colors, emoji = [s.GREEN, s.CYAN], "🎉"
            lines = [self._center("Acertou!", 30, color=DARK_TEXT), self._center(f"+{player.gain} pontos", 22, color=DARK_TEXT)]
        else:
            colors, emoji = ["#FF4D6D", s.ORANGE], ("💡" if player.choice is not None else "⏰")
            first = "Quase!" if player.choice is not None else "Não deu tempo!"
            lines = [
                self._center(first, 28),
                self._center(f"A certa era {answer}", 18),
                self._center(question.explanation, 14, weight=ft.FontWeight.W_600),
            ]
        feedback = ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=18),
            border_radius=26,
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT, colors=colors),
            content=ft.Column([self._center(emoji, 48), *lines], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )
        return [
            ft.Row([s.chip(f"PERGUNTA {self.quiz.number}/{self.quiz.total}", color=s.CYAN, size=13)], alignment=ft.MainAxisAlignment.CENTER),
            feedback,
            self._place_line(),
            self._center("Olhe para a tela: a próxima pergunta já vem!" if not self.quiz.is_last else "Olhe para a tela: vem aí o pódio!", 14, color=s.MUTED, weight=ft.FontWeight.W_600),
        ]

    def _final_items(self) -> list[ft.Control]:
        player = self.player
        place = self.quiz.place_of(player.id)
        key = (Phase.FINISHED, self.quiz.number)
        if self.sounded != key:
            self.sounded = key
            self.sounds.play("vitoria" if place == 1 else "incentivo")
        headline = "Você venceu o quiz! 🥇" if place == 1 else f"Você ficou em {place}º lugar!"
        return [
            self._title(),
            self._center("🏆", 64),
            self._center("Fim do quiz!", 30, color=s.YELLOW),
            self._center(headline, 22),
            self._center(
                f"{points_text(player.score)} pontos • {player.correct} de {self.quiz.total} acertos",
                16,
                weight=ft.FontWeight.W_600,
            ),
            self._center("Fique por aqui: pode ter outra rodada!", 14, color=s.MUTED, weight=ft.FontWeight.W_600),
            *self._suggestion_row(),
        ]

    def _suggestion_row(self) -> list[ft.Control]:
        if self.on_suggestion is None:
            return []
        return [
            ft.Row([suggestion_button(self._open_suggestion)], alignment=ft.MainAxisAlignment.CENTER),
            suggestion_qr("Prefere responder depois? Escaneie o QR code e responda em casa, com internet."),
        ]

    def _open_suggestion(self, _: Any = None) -> None:
        if self.on_suggestion is not None:
            SuggestionForm(self.page, self.on_suggestion).open()
