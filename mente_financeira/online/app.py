"""Telas do modo online: sala de espera e duelo entre dois computadores.

Roda no servidor (``servidor_online.py``): cada pessoa que abre o endereço é
uma sessão do Flet. As sessões compartilham uma só ``Lobby`` na memória e se
avisam pelo ``pubsub`` do Flet: quando alguém joga, a tela do adversário é
redesenhada com o mesmo jogo. Só pedimos um apelido, e nada é guardado.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse

import flet as ft

from mente_financeira.content.memory_deck import load_memory_deck
from mente_financeira.online.lobby import NICKNAME_MAX, Lobby, Match, NicknameError
from mente_financeira.storage import Settings, SettingsStore
from mente_financeira.ui import style as s
from mente_financeira.ui.memory_screen import MemoryScreen
from mente_financeira.ui.shell import MEMORY_TRACKS
from mente_financeira.ui.sounds import SoundEffects
from mente_financeira.ui.tracks import FUNDAMENTAL, TRACKS

ONLINE_TRACKS = tuple(t for t in TRACKS if t.key in MEMORY_TRACKS)
LOBBY_TOPIC = "sala"  # avisa todo mundo que a contagem de pessoas mudou


def player_topic(player_id: str) -> str:
    return f"jogador:{player_id}"


def new_lobby() -> Lobby:
    return Lobby([t.key for t in ONLINE_TRACKS], lambda track: load_memory_deck(MEMORY_TRACKS[track][0]))


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
    """Preferências (som) só na memória da sessão: nada vai para o disco do servidor."""

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
    """Liga a tela do jogo à partida online (veja ``OnlineSeat``)."""

    app: OnlineApp
    seat: int
    match: Match = field(repr=False)

    def changed(self) -> None:
        self.app.tell_opponent(self.match, {"kind": "sync"})


class OnlineApp:
    def __init__(self, page: ft.Page, lobby: Lobby, messenger: Messenger, *, player_id: str, track: str | None = None) -> None:
        self.page = page
        self.lobby = lobby
        self.messenger = messenger
        self.player_id = player_id
        self.track = track if track in lobby.tracks else FUNDAMENTAL
        self.nickname = ""
        self.sounds = SoundEffects(page, SessionStore())
        self.sounds.preload()
        self.game_screen: MemoryScreen | None = None
        self.count_labels: dict[str, ft.Text] = {}
        self.name_field = ft.TextField()
        self.page.title = "Mente Financeira • Duelo online"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.on_resize = None
        messenger.subscribe(player_topic(player_id), self._on_message)
        messenger.subscribe(LOBBY_TOPIC, self._on_lobby_changed)
        self.show_lobby()

    # ------------------------------------------------------------ recados
    def tell_opponent(self, match: Match, message: dict[str, Any]) -> None:
        opponent = match.opponent_of(self.player_id)
        if opponent.id not in match.left:
            self.messenger.send(player_topic(opponent.id), message)

    def _lobby_changed(self) -> None:
        self.messenger.send(LOBBY_TOPIC, {"kind": "counts"})

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

    async def _on_lobby_changed(self, _: dict[str, Any]) -> None:
        if self.game_screen is None and self.count_labels:
            self._refresh_counts()
            self.page.update()

    # ------------------------------------------------------------ saídas
    def leave(self) -> None:
        """Sai de tudo (fila ou partida) e avisa o adversário, se houver."""

        match = self.lobby.leave(self.player_id)
        if match is not None:
            self.tell_opponent(match, {"kind": "left", "nickname": self.nickname})
        self._lobby_changed()

    def close(self, _: Any = None) -> None:
        """A pessoa fechou a página: apaga tudo o que havia dela."""

        if self.game_screen is not None:
            self.game_screen.stop()
            self.game_screen = None
        self.leave()
        self.messenger.close()

    # ------------------------------------------------------------ sala
    def show_lobby(self, _: Any = None) -> None:
        if self.game_screen is not None:
            self.game_screen.stop()
            self.game_screen = None
        self.lobby.browse(self.player_id, self.track)
        self._lobby_changed()
        self._render(self._lobby_panel())

    def back_to_lobby(self) -> None:
        self.leave()
        self.show_lobby()

    def _choose_track(self, event: Any) -> None:
        self.track = event.control.data
        self.nickname = self.name_field.value or self.nickname
        self.show_lobby()

    def _search(self, _: Any = None) -> None:
        try:
            match = self.lobby.wait(self.player_id, self.name_field.value or "", self.track)
        except NicknameError as error:
            self.name_field.error = str(error)
            self.page.update()
            return
        self.nickname = self.lobby.waiting[self.track].nickname if match is None else match.players[1].nickname
        self._lobby_changed()
        if match is None:
            self._render(self._waiting_panel())
            return
        self.tell_opponent(match, {"kind": "start"})
        self.start_match(match)

    def _cancel(self, _: Any = None) -> None:
        self.show_lobby()

    def start_match(self, match: Match) -> None:
        seat = match.seat_of(self.player_id)
        self.count_labels = {}
        screen = MemoryScreen(
            self.page,
            match.game,
            on_home=self.back_to_lobby,
            on_level2=self.back_to_lobby,
            sounds=self.sounds,
            challenges=MEMORY_TRACKS[match.track][1],
            online=Seat(self, seat, match),
        )
        self.game_screen = screen
        self.page.on_resize = screen.on_resize
        screen.show()
        opponent = match.opponent_of(self.player_id).nickname
        first = match.game.current_player
        screen._snack(f"Partida contra {opponent}! Começa {first}." if seat else f"Partida contra {opponent}! Você começa. 🎯")
        self.page.update()

    # ------------------------------------------------------------ desenho
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

    def _glass(self, items: list[ft.Control]) -> ft.Container:
        return ft.Container(
            width=560,
            padding=24,
            border_radius=32,
            bgcolor=ft.Colors.with_opacity(0.10, s.WHITE),
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.35, s.CYAN)),
            shadow=ft.BoxShadow(blur_radius=60, color=ft.Colors.with_opacity(0.35, "#6C63FF")),
            content=ft.Column(items, spacing=16, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        )

    def _title(self) -> ft.Control:
        return ft.Column(
            [
                s.gradient_text("MENTE", 50, [s.YELLOW, s.ORANGE, s.PINK]),
                s.gradient_text("FINANCEIRA", 32, [s.CYAN, "#8F88FF", s.PINK]),
                ft.Row([s.chip("DUELO ONLINE", icon=ft.Icons.PUBLIC_ROUNDED, color=s.CYAN, size=12)], alignment=ft.MainAxisAlignment.CENTER),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _count_text(self, key: str) -> str:
        count = self.lobby.counts().get(key, 0)
        return "1 pessoa online" if count == 1 else f"{count} pessoas online"

    def _refresh_counts(self) -> None:
        for key, label in self.count_labels.items():
            label.value = self._count_text(key)

    def _track_tile(self, track: Any) -> ft.Container:
        selected = track.key == self.track
        first, second = track.colors
        label = ft.Text(self._count_text(track.key), size=12, weight=ft.FontWeight.BOLD, color=s.WHITE)
        self.count_labels[track.key] = label
        look: dict[str, Any] = (
            {"gradient": ft.LinearGradient(colors=[first, second]), "border": ft.Border.all(2, s.WHITE)}
            if selected
            else {"bgcolor": ft.Colors.with_opacity(0.10, first), "border": ft.Border.all(1.5, ft.Colors.with_opacity(0.55, first))}
        )
        return ft.Container(
            data=track.key,
            on_click=self._choose_track,
            ink=True,
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            border_radius=20,
            content=ft.Row(
                [
                    ft.Icon(track.icon, color=s.WHITE, size=28),
                    ft.Column(
                        [ft.Text(track.title, size=16, weight=ft.FontWeight.W_900, color=s.WHITE), label],
                        spacing=1,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED if selected else ft.Icons.RADIO_BUTTON_UNCHECKED, color=s.WHITE),
                ],
                spacing=12,
            ),
            **look,
        )

    def _lobby_panel(self) -> ft.Control:
        self.count_labels = {}
        self.name_field = ft.TextField(
            value=self.nickname,
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
            on_submit=self._search,
        )
        return self._glass(
            [
                self._title(),
                ft.Text("Escolha a trilha", size=20, weight=ft.FontWeight.W_900, color=s.WHITE),
                *[self._track_tile(track) for track in ONLINE_TRACKS],
                self.name_field,
                s.pill_button("PROCURAR ADVERSÁRIO", ft.Icons.SEARCH_ROUNDED, self._search, height=58),
                ft.Text(
                    "🔒 Só pedimos um apelido (não use seu nome completo). Nada fica guardado depois que você sai.",
                    size=12,
                    color=s.MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
            ]
        )

    def _waiting_panel(self) -> ft.Control:
        self.count_labels = {}
        track = next(t for t in ONLINE_TRACKS if t.key == self.track)
        label = ft.Text(self._count_text(track.key), size=13, weight=ft.FontWeight.BOLD, color=s.CYAN, text_align=ft.TextAlign.CENTER)
        self.count_labels[track.key] = label
        return self._glass(
            [
                self._title(),
                ft.Row([ft.ProgressRing(color=s.YELLOW, width=48, height=48, stroke_width=5)], alignment=ft.MainAxisAlignment.CENTER),
                ft.Text(
                    f"Olá, {self.nickname}! Esperando alguém para jogar",
                    size=20,
                    weight=ft.FontWeight.W_900,
                    color=s.WHITE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(track.title, size=15, color=s.WHITE, text_align=ft.TextAlign.CENTER),
                label,
                ft.Text(
                    "A partida começa sozinha quando outra pessoa entrar nesta trilha.",
                    size=12,
                    color=s.MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.TextButton("Cancelar", icon=ft.Icons.CLOSE_ROUNDED, on_click=self._cancel, style=ft.ButtonStyle(color=s.CYAN)),
            ]
        )


def track_from_route(route: str | None) -> str | None:
    """Trilha pedida no endereço (``/?trilha=fundamental1``)."""

    values = parse_qs(urlparse(route or "").query).get("trilha")
    return values[0] if values else None


def make_main(lobby: Lobby) -> Callable[[ft.Page], None]:
    """Ponto de entrada de cada sessão no servidor, todas com a mesma sala."""

    def main(page: ft.Page) -> None:
        track = track_from_route(page.route)  # vem do botão "Jogar online" do site
        app = OnlineApp(page, lobby, PubSubMessenger(page), player_id=page.session.id, track=track)
        page.on_close = app.close

    return main
