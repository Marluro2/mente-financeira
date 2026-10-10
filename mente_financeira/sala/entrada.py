"""Porta de entrada de cada aparelho no servidor da feira.

Pelo endereço, cada sessão abre a tela certa:

- ``/`` ou ``/?sala=GATO-42``: Duelo em sala (celular contra celular);
- ``/?quiz=jogar``: Quiz ao vivo, no celular de quem responde;
- ``/?quiz=apresentar``: Quiz ao vivo, na tela do notebook (só no próprio notebook).
"""

from __future__ import annotations

from collections.abc import Callable, Collection

import flet as ft

from mente_financeira.sala.app import PubSubMessenger, RoomApp, code_from_route
from mente_financeira.sala.quiz import Quiz
from mente_financeira.sala.quiz_app import PRESENT, QuizHost, QuizPhone, is_local, quiz_role
from mente_financeira.sala.ranking import FairRanking
from mente_financeira.sala.salas import Lobby, RoomError, normalize_code
from mente_financeira.sugestoes import Suggestion


def make_main(
    lobby: Lobby,
    quiz: Quiz,
    on_suggestion: Callable[[Suggestion], None] | None = None,
    *,
    join_url: str = "",
    own_ips: Collection[str] = (),
    ranking: FairRanking | None = None,
) -> Callable[[ft.Page], None]:
    """Ponto de entrada de cada aparelho, todos com as mesmas salas e o mesmo quiz.

    ``join_url`` é o endereço do quiz escrito no telão; ``own_ips``, os IPs do notebook;
    ``ranking``, o placar do dia (Duelo e Quiz) mostrado no cartaz.
    """

    def main(page: ft.Page) -> None:
        messenger = PubSubMessenger(page)
        role = quiz_role(page.route)
        if role == PRESENT and is_local(page.client_ip, own_ips):
            host = QuizHost(page, quiz, messenger, session_id=page.session.id, join_url=join_url, ranking=ranking)
            page.on_close = host.close
            return
        if role is not None:
            phone = QuizPhone(page, quiz, messenger, session_id=page.session.id, on_suggestion=on_suggestion)
            page.on_close = phone.close
            return
        raw = code_from_route(page.route)
        try:
            code = normalize_code(raw) if raw else None
        except RoomError:
            code = None
        app = RoomApp(
            page, lobby, messenger, player_id=page.session.id, code=code, on_suggestion=on_suggestion, ranking=ranking
        )
        page.on_close = app.close

    return main
