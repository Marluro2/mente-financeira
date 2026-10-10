"""Telas do Duelo em sala: criar sala, entrar com código e jogar.

Roda no notebook (``servidor_sala.py``), sem internet: cada celular que abre o
endereço do notebook é uma sessão do Flet. As sessões compartilham as salas na
memória e se avisam pelo ``pubsub`` do Flet: quando alguém joga, a tela do
adversário é redesenhada com o mesmo jogo. Só pedimos um apelido, e nada é
guardado.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse

import flet as ft

from mente_financeira.content.memory_deck import load_memory_deck
from mente_financeira.sala.ranking import DUEL, FairRanking
from mente_financeira.sala.salas import NICKNAME_MAX, Lobby, Match, NicknameError, Room, RoomError, normalize_code
from mente_financeira.storage import Settings, SettingsStore
from mente_financeira.sugestoes import Suggestion
from mente_financeira.ui import style as s
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.shell import MEMORY_TRACKS
from mente_financeira.ui.sounds import SoundEffects
from mente_financeira.ui.suggestion_form import SuggestionForm, suggestion_button, suggestion_qr
from mente_financeira.ui.tracks import FUNDAMENTAL, TRACKS

ROOM_TRACKS = tuple(t for t in TRACKS if t.key in MEMORY_TRACKS)


def player_topic(player_id: str) -> str:
    return f"jogador:{player_id}"


def room_qr_path(code: str) -> str:
    """QR code com o endereço da sala (desenhado pelo servidor)."""

    return f"/qr/sala/{code}.png"


def new_lobby() -> Lobby:
    return Lobby([t.key for t in ROOM_TRACKS], lambda track: load_memory_deck(MEMORY_TRACKS[track][0]))


def code_from_route(route: str | None) -> str | None:
    """Código pedido no endereço (``/?sala=GATO-42``, vindo do QR code)."""

    values = parse_qs(urlparse(route or "").query).get("sala")
    return values[0] if values else None


class Messenger(Protocol):
    """Recados entre sessões (no servidor, o ``pubsub`` do Flet)."""

    def subscribe(self, topic: str, handler: Callable[[dict[str, Any]], Awaitable[None]]) -> None: ...

    def send(self, topic: str, message: dict[str, Any]) -> None: ...

    def close(self) -> None: ...


class PubSubMessenger:
    def __init__(self, page: ft.Page) -> None:
        self.pubsub = page.pubsub

    def subscribe(self, topic: str, handler: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        async def receive(_topic: str, message: dict[str, Any]) -> None:
            await handler(message)

        self.pubsub.subscribe_topic(topic, receive)

    def send(self, topic: str, message: dict[str, Any]) -> None:
        self.pubsub.send_all_on_topic(topic, message)

    def close(self) -> None:
        self.pubsub.unsubscribe_all()


class SessionStore(SettingsStore):
    """Preferências (som) só na memória da sessão: nada vai para o disco do notebook."""

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()

    def load(self) -> Settings:
        return replace(self.settings)

    def save(self, settings: Settings) -> bool:
        self.settings = settings
        return True


@dataclass(slots=True)
class Seat:
    """Liga a tela do jogo à partida da sala (veja ``OnlineSeat``)."""

    app: RoomApp
    seat: int
    match: Match = field(repr=False)

    def changed(self) -> None:
        self.app.match_changed(self.match)
        self.app.tell_opponent(self.match, {"kind": "sync"})


class RoomApp:
    def __init__(
        self,
        page: ft.Page,
        lobby: Lobby,
        messenger: Messenger,
        *,
        player_id: str,
        code: str | None = None,
        on_suggestion: Callable[[Suggestion], None] | None = None,
        ranking: FairRanking | None = None,
    ) -> None:
        self.page = page
        self.on_suggestion = on_suggestion  # guarda a sugestão no notebook
        self.ranking = ranking  # placar do dia no cartaz do estande
        self.lobby = lobby
        self.messenger = messenger
        self.player_id = player_id
        self.track = FUNDAMENTAL
        self.nickname = ""
        self.code = code or ""  # veio do QR code da sala: é só entrar
        self.sounds = SoundEffects(page, SessionStore())
        self.sounds.preload()
        self.game_screen: MemoryScreen | None = None
        self.name_field = ft.TextField()
        self.code_field = ft.TextField()
        self.page.title = "Mente Financeira • Duelo em sala"
        self.page.padding = 0
        self.page.spacing = 0
        messenger.subscribe(player_topic(player_id), self._on_message)
        self.show_start()

    # ------------------------------------------------------------ recados
    def tell_opponent(self, match: Match, message: dict[str, Any]) -> None:
        opponent = match.opponent_of(self.player_id)
        if opponent.id not in match.left:
            self.messenger.send(player_topic(opponent.id), message)

    async def _on_message(self, message: dict[str, Any]) -> None:
        kind = message.get("kind")
        if kind == "start":
            match = self.lobby.matches.get(self.player_id)
            if match is not None:
                self.start_match(match)
        elif kind == "sync" and self.game_screen is not None:
            self.game_screen.sync()
        elif kind == "left" and self.game_screen is not None:
            self.game_screen.opponent_left(str(message.get("nickname", "O adversário")))

    def match_changed(self, match: Match) -> None:
        """Partida terminada: os pontos dos dois entram no ranking da feira."""

        if self.ranking is not None and match.game.is_complete:
            title = next(t.title for t in ROOM_TRACKS if t.key == match.track)
            self.ranking.record(DUEL, match.id, zip((p.nickname for p in match.players), match.game.points), title)

    # ------------------------------------------------------------ saídas
    def leave(self) -> None:
        """Fecha a sala ou sai da partida e avisa o adversário, se houver."""

        if self.game_screen is not None:
            self.game_screen.stop()
            self.game_screen = None
        match = self.lobby.leave(self.player_id)
        if match is not None:
            self.tell_opponent(match, {"kind": "left", "nickname": self.nickname})

    def close(self, _: Any = None) -> None:
        """A pessoa fechou a página: apaga tudo o que havia dela."""

        self.leave()
        self.messenger.close()

    def back_to_start(self) -> None:
        self.code = ""
        self.leave()
        self.show_start()

    # ------------------------------------------------------------ ações
    def _remember_fields(self) -> None:
        self.nickname = self.name_field.value or ""
        self.code = self.code_field.value or ""

    def _choose_track(self, event: Any) -> None:
        self._remember_fields()
        self.track = event.control.data
        self.show_start()

    def _create(self, _: Any = None) -> None:
        self._remember_fields()
        try:
            room = self.lobby.create_room(self.player_id, self.nickname, self.track)
        except NicknameError as error:
            self.name_field.error = str(error)
            self.page.update()
            return
        self.nickname = room.host.nickname
        self._render(self._waiting_panel(room))

    def _join(self, _: Any = None) -> None:
        self._remember_fields()
        self.name_field.error = self.code_field.error = None
        try:
            match = self.lobby.join(self.player_id, self.nickname, self.code)
        except NicknameError as error:
            self.name_field.error = str(error)
            self.page.update()
            return
        except RoomError as error:
            self.code_field.error = str(error)
            self.page.update()
            return
        self.nickname = match.players[1].nickname
        self.tell_opponent(match, {"kind": "start"})
        self.start_match(match)

    def _cancel(self, _: Any = None) -> None:
        self.lobby.leave(self.player_id)
        self.show_start()

    def start_match(self, match: Match) -> None:
        seat = match.seat_of(self.player_id)
        screen = MemoryScreen(
            self.page,
            match.game,
            on_home=self.back_to_start,
            on_level2=self.back_to_start,
            sounds=self.sounds,
            challenges=MEMORY_TRACKS[match.track][1],
            online=Seat(self, seat, match),
        )
        self.game_screen = screen
        self.page.on_resize = screen.on_resize
        screen.show()
        opponent = match.opponent_of(self.player_id).nickname
        screen._snack(f"Partida contra {opponent}! " + ("Você começa. 🎯" if seat == 0 else f"Começa {opponent}."))
        self.page.update()

    # ------------------------------------------------------------ desenho
    def show_start(self, _: Any = None) -> None:
        self._render(self._start_panel())

    def _render(self, panel: ft.Control) -> None:
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
                        [
                            ft.Row(
                                [ft.Container(padding=ft.Padding.symmetric(horizontal=12, vertical=24), content=panel)],
                                alignment=ft.MainAxisAlignment.CENTER,
                            )
                        ],
                        scroll=ft.ScrollMode.AUTO,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            )
        )
        self.page.update()

    def _panel(self, items: list[ft.Control]) -> ft.Container:
        width = self.page.width or 400
        return ft.Container(
            width=min(540, width - 24),
            padding=ft.Padding.symmetric(horizontal=16, vertical=22),
            border_radius=28,
            bgcolor=ft.Colors.with_opacity(0.10, s.WHITE),
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.35, s.CYAN)),
            shadow=ft.BoxShadow(blur_radius=60, color=ft.Colors.with_opacity(0.35, "#6C63FF")),
            content=ft.Column(items, spacing=14, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        )

    def _title(self) -> ft.Control:
        return ft.Column(
            [
                s.gradient_text("MENTE", 46, [s.YELLOW, s.ORANGE, s.PINK]),
                s.gradient_text("FINANCEIRA", 30, [s.CYAN, "#8F88FF", s.PINK]),
                ft.Row(
                    [s.chip("DUELO EM SALA", icon=ft.Icons.PEOPLE_ALT_ROUNDED, color=s.CYAN, size=12)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _field(self, label: str, value: str, icon: ft.IconData, *, max_length: int, on_submit: Callable[[Any], None], **extra: Any) -> ft.TextField:
        return ft.TextField(
            value=value,
            label=label,
            max_length=max_length,
            border_radius=16,
            filled=True,
            bgcolor=ft.Colors.with_opacity(0.10, s.WHITE),
            border_color=s.GLASS_BORDER,
            focused_border_color=s.CYAN,
            color=s.WHITE,
            label_style=ft.TextStyle(color=s.MUTED),
            prefix_icon=icon,
            on_submit=on_submit,
            **extra,
        )

    def _heading(self, text: str) -> ft.Text:
        return ft.Text(text, size=18, weight=ft.FontWeight.W_900, color=s.WHITE)

    def _track_tile(self, track: Any) -> ft.Container:
        selected = track.key == self.track
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
                    ft.Text(track.title, size=15, weight=ft.FontWeight.W_900, color=s.WHITE, expand=True),
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED if selected else ft.Icons.RADIO_BUTTON_UNCHECKED, color=s.WHITE),
                ],
                spacing=12,
            ),
            **look,
        )

    def _start_panel(self) -> ft.Control:
        self.name_field = self._field(
            "Seu apelido", self.nickname, ft.Icons.BADGE_OUTLINED, max_length=NICKNAME_MAX, on_submit=self._create, hint_text="Ex.: Lia, Pedro10"
        )
        self.code_field = self._field(
            "Código da sala",
            self.code,
            ft.Icons.KEY_ROUNDED,
            max_length=9,
            on_submit=self._join,
            hint_text="Ex.: GATO-42",
            capitalization=ft.TextCapitalization.CHARACTERS,
        )
        create = [
            self._heading("Criar uma sala"),
            *[self._track_tile(track) for track in ROOM_TRACKS],
            s.pill_button("CRIAR SALA", ft.Icons.ADD_ROUNDED, self._create, height=54),
        ]
        join = [
            self._heading("Entrar numa sala"),
            self.code_field,
            s.pill_button("ENTRAR", ft.Icons.LOGIN_ROUNDED, self._join, height=54, colors=[s.CYAN, "#6C63FF"]),
        ]
        either = ft.Row(
            [
                ft.Container(height=1, expand=True, bgcolor=s.GLASS_BORDER),
                ft.Text("ou", color=s.MUTED, weight=ft.FontWeight.BOLD),
                ft.Container(height=1, expand=True, bgcolor=s.GLASS_BORDER),
            ],
            spacing=10,
        )
        # Quem chegou pelo QR code da sala já tem o código: entrar vem primeiro.
        sections = [*join, either, *create] if self.code else [*create, either, *join]
        return self._panel(
            [
                self._title(),
                self.name_field,
                *sections,
                ft.Text(
                    "Só pedimos um apelido (não use seu nome completo). Ele pode aparecer no ranking do estande "
                    "até o fim do dia; nada fica gravado.",
                    size=12,
                    color=s.MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                *self._suggestion_row(),
            ]
        )

    def _suggestion_row(self) -> list[ft.Control]:
        if self.on_suggestion is None:
            return []
        return [
            ft.Row([suggestion_button(self._open_suggestion)], alignment=ft.MainAxisAlignment.CENTER),
            # Sem internet na feira: o QR fica para a pessoa responder depois, em casa.
            suggestion_qr("Prefere responder depois? Escaneie o QR code e responda em casa, com internet."),
        ]

    def _open_suggestion(self, _: Any = None) -> None:
        if self.on_suggestion is not None:
            SuggestionForm(self.page, self.on_suggestion).open()

    def _waiting_panel(self, room: Room) -> ft.Control:
        track = next(t for t in ROOM_TRACKS if t.key == room.track)
        return self._panel(
            [
                self._title(),
                ft.Text(f"Olá, {room.host.nickname}! Sua sala é:", size=16, color=s.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text(room.code, size=44, weight=ft.FontWeight.W_900, color=s.YELLOW, text_align=ft.TextAlign.CENTER, selectable=True),
                ft.Row(
                    [
                        ft.Container(
                            padding=10,
                            border_radius=18,
                            bgcolor=s.WHITE,
                            content=ft.Image(src=room_qr_path(room.code), width=200, height=200, semantics_label=f"QR code da sala {room.code}"),
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Text(
                    "A outra pessoa escaneia este QR code ou digita o código no celular dela.",
                    size=14,
                    color=s.WHITE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Row(
                    [ft.ProgressRing(color=s.YELLOW, width=22, height=22, stroke_width=3), ft.Text(f"Esperando... • {track.title}", color=s.CYAN, weight=ft.FontWeight.BOLD)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.TextButton("Cancelar", icon=ft.Icons.CLOSE_ROUNDED, on_click=self._cancel, style=ft.ButtonStyle(color=s.CYAN)),
            ]
        )

