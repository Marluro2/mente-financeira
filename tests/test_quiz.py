"""Quiz ao vivo da feira: regras, telão do notebook, celulares e servidor."""

from __future__ import annotations

import asyncio
import random
from types import SimpleNamespace
from typing import Any

import flet as ft
import pytest
from fastapi.testclient import TestClient

from fakes import FakeHub, FakePage, walk
from mente_financeira.core.percent_challenge import PERCENT_KIT
from mente_financeira.sala import quiz_app
from mente_financeira.sala.app import RoomApp, new_lobby
from mente_financeira.sala.entrada import make_main
from mente_financeira.sala.quiz import (
    CORRECT_POINTS,
    PLAYERS_MAX,
    SPEED_POINTS,
    Phase,
    Quiz,
    QuizError,
    draw_questions,
)
from mente_financeira.sala.quiz_app import PLAY, PRESENT, QUIZ_QR_PATH, QuizHost, QuizPhone, is_local, new_quiz, quiz_role
from mente_financeira.sala.salas import NicknameError
from mente_financeira.ui.tracks import ENGENHARIA, FUNDAMENTAL, FUNDAMENTAL_1
import servidor_sala


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def quiz(clock: Clock) -> Quiz:
    return Quiz({FUNDAMENTAL: PERCENT_KIT}, FUNDAMENTAL, count=3, seconds=20, rng=random.Random(5), clock=clock)


def _right(quiz: Quiz) -> int:
    assert quiz.question is not None
    return quiz.question.answer_index


def _wrong(quiz: Quiz) -> int:
    return (_right(quiz) + 1) % 4


# ====================================================================== regras
def test_questions_do_not_repeat_and_come_from_every_track() -> None:
    for key, kit in new_quiz().kits.items():
        questions = draw_questions(kit, 8, random.Random(2))
        assert len(questions) == 8, key
        assert len({q.question for q in questions}) == 8
        assert all(len(q.options) == 4 for q in questions)
    assert set(new_quiz().kits) == {FUNDAMENTAL_1, FUNDAMENTAL, ENGENHARIA}


def test_join_asks_only_for_a_nickname_and_refuses_repeated_ones(quiz: Quiz) -> None:
    quiz.join("a", "  Lia  ")
    assert quiz.players["a"].nickname == "Lia"
    with pytest.raises(NicknameError):
        quiz.join("b", "lia")
    with pytest.raises(NicknameError):
        quiz.join("b", "x")
    quiz.join("a", "Lia2")  # a mesma pessoa pode trocar de apelido
    assert [p.nickname for p in quiz.players.values()] == ["Lia2"]


def test_quiz_has_a_limit_of_players(quiz: Quiz) -> None:
    for n in range(PLAYERS_MAX):
        quiz.join(str(n), f"P{n}")
    with pytest.raises(QuizError):
        quiz.join("extra", "Extra")


def test_start_needs_someone_and_opens_the_first_question(quiz: Quiz, clock: Clock) -> None:
    with pytest.raises(QuizError):
        quiz.start()
    quiz.join("a", "Ana")
    quiz.start()
    assert quiz.phase is Phase.QUESTION and quiz.number == 1 and quiz.total == 3
    assert quiz.remaining() == 20
    clock.now += 4.2
    assert quiz.remaining() == 16
    with pytest.raises(QuizError):
        quiz.start()


def test_faster_right_answers_score_more(quiz: Quiz, clock: Clock) -> None:
    for pid, name in (("a", "Ana"), ("b", "Bia"), ("c", "Caio")):
        quiz.join(pid, name)
    quiz.start()
    assert quiz.answer("a", _right(quiz))  # na hora: bônus inteiro
    clock.now += 10
    assert quiz.answer("b", _right(quiz))  # na metade do tempo: metade do bônus
    assert quiz.answer("c", _wrong(quiz))
    assert not quiz.answer("a", _wrong(quiz))  # só vale a primeira resposta
    assert not quiz.answer("x", 0)  # quem não entrou não responde
    assert [p.score for p in quiz.players.values()] == [0, 0, 0]  # pontos só na revelação
    assert quiz.all_answered and quiz.answered == 3

    assert quiz.reveal(1)
    scores = {p.nickname: p.score for p in quiz.players.values()}
    assert scores == {"Ana": CORRECT_POINTS + SPEED_POINTS, "Bia": CORRECT_POINTS + SPEED_POINTS // 2, "Caio": 0}
    assert [p.nickname for p in quiz.ranking()] == ["Ana", "Bia", "Caio"]
    assert quiz.distribution()[_right(quiz)] == 2


def test_late_answers_and_double_reveals_do_not_count(quiz: Quiz, clock: Clock) -> None:
    quiz.join("a", "Ana")
    quiz.start()
    clock.now += 20
    assert quiz.time_up and quiz.remaining() == 0
    assert not quiz.answer("a", _right(quiz))
    assert not quiz.reveal(2)  # outra pergunta
    assert quiz.reveal(1)
    assert not quiz.reveal(1)  # o telão e o último celular podem revelar juntos
    assert quiz.players["a"].score == 0


def test_rounds_go_to_the_podium_and_count_streaks(quiz: Quiz) -> None:
    quiz.join("a", "Ana")
    quiz.join("b", "Bia")
    quiz.start()
    for number in (1, 2, 3):
        quiz.answer("a", _right(quiz))
        quiz.answer("b", _wrong(quiz) if number == 2 else _right(quiz))
        assert not quiz.advance(number)  # antes da resposta aparecer, não avança
        assert quiz.reveal(number)
        assert not quiz.advance(number + 1)
        if number < 3:
            assert not quiz.is_last
            assert quiz.advance(number)
            assert quiz.phase is Phase.QUESTION and quiz.number == number + 1
            assert all(p.choice is None for p in quiz.players.values())
    assert quiz.is_last and quiz.advance(3)
    assert quiz.phase is Phase.FINISHED
    ana, bia = quiz.players["a"], quiz.players["b"]
    assert (ana.correct, ana.streak) == (3, 3)
    assert (bia.correct, bia.streak) == (2, 1)


def test_ties_share_the_place(quiz: Quiz) -> None:
    for pid, name in (("a", "Ana"), ("b", "Bia"), ("c", "Caio")):
        quiz.join(pid, name)
    quiz.players["a"].score = quiz.players["b"].score = 300
    quiz.players["c"].score = 100
    assert [quiz.place_of(pid) for pid in "abc"] == [1, 1, 3]


def test_track_changes_only_in_the_lobby_and_restart_keeps_people(clock: Clock) -> None:
    quiz = new_quiz()
    quiz.clock = clock
    with pytest.raises(QuizError):
        quiz.choose_track("medio")
    quiz.choose_track(ENGENHARIA)
    quiz.join("a", "Ana")
    quiz.start()
    assert quiz.question is not None and quiz.question.label in {"PAYBACK", "VALOR PRESENTE", "VPL: VALE A PENA?"}
    quiz.choose_track(FUNDAMENTAL)
    assert quiz.track == ENGENHARIA
    quiz.answer("a", _right(quiz))
    quiz.reveal(1)
    quiz.restart()
    assert quiz.phase is Phase.LOBBY and quiz.question is None
    assert quiz.players["a"].score == 0 and quiz.players["a"].nickname == "Ana"
    assert quiz.leave("a") is not None and quiz.leave("a") is None


# ====================================================================== telas
def _texts(page: FakePage) -> list[str]:
    return [c.value for c in walk(page.controls[-1]) if isinstance(c, ft.Text) and isinstance(c.value, str)]


def _joined_text(page: FakePage) -> str:
    return " | ".join(_texts(page))


def _host(hub: FakeHub, quiz: Quiz) -> QuizHost:
    return QuizHost(FakePage(1280, 720), quiz, hub.messenger("host"), session_id="host", join_url="http://192.168.0.10:8000/?quiz=jogar")  # type: ignore[arg-type]


def _phone(hub: FakeHub, quiz: Quiz, pid: str, nickname: str | None = None) -> QuizPhone:
    phone = QuizPhone(FakePage(390, 844), quiz, hub.messenger(pid), session_id=pid)  # type: ignore[arg-type]
    if nickname is not None:
        phone.name_field.value = nickname
        phone._join()
        hub.flush()
    return phone


def _tap(phone: QuizPhone, choice: int, hub: FakeHub) -> None:
    phone._answer(SimpleNamespace(control=SimpleNamespace(data=choice)))
    hub.flush()


def _option_buttons(page: FakePage) -> list[Any]:
    return [c for c in walk(page.controls[-1]) if isinstance(c, ft.Container) and c.on_click is not None and isinstance(c.data, int)]


def test_quiz_role_and_host_only_on_the_notebook() -> None:
    assert quiz_role("/?quiz=jogar") == PLAY
    assert quiz_role("/?quiz=APRESENTAR") == PRESENT
    assert quiz_role("/?quiz=qualquer") == PLAY
    assert quiz_role("/") is None and quiz_role(None) is None
    assert is_local("127.0.0.1") and is_local("::1")
    assert not is_local("192.168.0.20")
    assert is_local("192.168.0.10", ["192.168.0.10"])


def test_host_lobby_shows_qr_and_who_joined(quiz: Quiz) -> None:
    hub = FakeHub()
    host = _host(hub, quiz)
    images = [c.src for c in walk(host.page.controls[-1]) if isinstance(c, ft.Image)]
    assert QUIZ_QR_PATH in images
    assert "Ninguém entrou ainda. Escaneie o QR code!" in _texts(host.page)
    assert "ou abra http://192.168.0.10:8000/?quiz=jogar" in _texts(host.page)

    host._start()  # sem ninguém: avisa e não começa
    assert host.error_text.visible and quiz.phase is Phase.LOBBY

    _phone(hub, quiz, "a", "Lia")
    assert "Jogadores: 1" in _texts(host.page) and "Lia" in _texts(host.page)


def test_phone_join_errors_and_typing_is_not_erased(quiz: Quiz) -> None:
    hub = FakeHub()
    _phone(hub, quiz, "a", "Lia")
    bia = _phone(hub, quiz, "b")
    bia.name_field.value = "lia"
    bia._join()
    assert bia.name_field.error == "Esse apelido já está no quiz. Escolha outro."
    field = bia.name_field
    _phone(hub, quiz, "c", "Caio")  # recado de "entrou gente" não redesenha quem está digitando
    assert bia.name_field is field
    bia.name_field.value = "Bia"
    bia._join()
    hub.flush()
    assert "Você está no quiz, Bia! 🎉" in _texts(bia.page)
    assert "3 pessoas no quiz • Ensino Fundamental 2" in _texts(bia.page)


def test_full_round_between_notebook_and_phones(quiz: Quiz, clock: Clock) -> None:
    hub = FakeHub()
    host = _host(hub, quiz)
    ana, bia = _phone(hub, quiz, "a", "Ana"), _phone(hub, quiz, "b", "Bia")

    host._start()
    hub.flush()
    question = quiz.question
    assert question is not None
    assert question.question in _texts(host.page) and "PERGUNTA 1 DE 3" in _texts(host.page)
    assert "0 de 2 responderam" in _texts(host.page)
    assert len(_option_buttons(ana.page)) == 4 and question.question in _texts(ana.page)

    _tap(ana, _right(quiz), hub)
    assert "Resposta enviada! ⏳" in _texts(ana.page)
    assert host.answered_text.value == "1 de 2 responderam"
    assert quiz.phase is Phase.QUESTION

    clock.now += 10
    _tap(bia, _wrong(quiz), hub)  # todo mundo respondeu: a resposta aparece na hora
    assert quiz.phase is Phase.REVEAL
    assert "Acertou!" in _texts(ana.page) and f"+{CORRECT_POINTS + SPEED_POINTS} pontos" in _texts(ana.page)
    assert "Quase!" in _texts(bia.page)
    assert f"A certa era {'ABCD'[question.answer_index]}) {question.answer}" in _texts(bia.page)
    assert "🥇 1º lugar" in _texts(ana.page) and "🥈 2º lugar" in _texts(bia.page)
    assert ana.sounds.history[-1] == "incentivo" and bia.sounds.history[-1] == "erro"
    assert "PLACAR" in _texts(host.page) and "1 de 2 acertaram" in _texts(host.page)
    assert question.explanation in _texts(host.page)

    for number in (1, 2):
        host._next()
        hub.flush()
        assert quiz.number == number + 1
        assert len(_option_buttons(bia.page)) == 4
        host._reveal()  # "Mostrar a resposta agora"
        hub.flush()
        assert "Não deu tempo!" in _texts(bia.page)
    assert "VER O PÓDIO" in _texts(host.page)
    host._next()
    hub.flush()
    assert quiz.phase is Phase.FINISHED
    assert "PÓDIO" in _texts(host.page) and host.sounds.history.count("vitoria") == 1
    assert "Você venceu o quiz! 🥇" in _texts(ana.page) and ana.sounds.history[-1] == "vitoria"
    assert "Você ficou em 2º lugar!" in _texts(bia.page)
    assert "1 de 3 acertos" in _joined_text(ana.page)

    host._restart()  # NOVO QUIZ: as mesmas pessoas voltam para a espera
    hub.flush()
    assert quiz.phase is Phase.LOBBY
    assert "Você está no quiz, Ana! 🎉" in _texts(ana.page)
    assert "Jogadores: 2" in _texts(host.page)


def test_clock_reveals_the_answer_when_time_is_up(quiz: Quiz, clock: Clock, monkeypatch: pytest.MonkeyPatch) -> None:
    hub = FakeHub()
    host = _host(hub, quiz)
    phone = _phone(hub, quiz, "a", "Ana")
    host._start()
    hub.flush()
    handler, args = host.page.tasks[-1]
    phone_handler, phone_args = phone.page.tasks[-1]

    async def tick(_: float) -> None:
        clock.now += 6

    monkeypatch.setattr(quiz_app.asyncio, "sleep", tick)
    asyncio.run(phone_handler(*phone_args))  # o celular só mostra "Tempo esgotado"
    assert "Tempo esgotado!" in _texts(phone.page) and quiz.phase is Phase.QUESTION
    asyncio.run(handler(*args))
    assert quiz.phase is Phase.REVEAL
    hub.flush()
    assert "Não deu tempo!" in _texts(phone.page)


def test_host_countdown_turns_red_at_the_end(quiz: Quiz, clock: Clock) -> None:
    hub = FakeHub()
    host = _host(hub, quiz)
    _phone(hub, quiz, "a", "Ana")
    host._start()
    hub.flush()
    assert host.countdown_text.value == "20"
    clock.now += 16
    host._set_countdown(quiz.remaining())
    assert host.countdown_text.value == "4" and host.countdown_ring.color == "#FF4D6D"


def test_leaving_removes_the_nickname(quiz: Quiz) -> None:
    hub = FakeHub()
    host = _host(hub, quiz)
    phone = _phone(hub, quiz, "a", "Lia")
    phone.close()
    hub.flush()
    assert quiz.players == {}
    assert "Ninguém entrou ainda. Escaneie o QR code!" in _texts(host.page)


def test_phone_can_join_a_quiz_already_running(quiz: Quiz) -> None:
    hub = FakeHub()
    host = _host(hub, quiz)
    _phone(hub, quiz, "a", "Ana")
    host._start()
    hub.flush()
    late = _phone(hub, quiz, "b")
    assert "O quiz já começou, mas dá para entrar agora!" in _texts(late.page)
    late.name_field.value = "Bia"
    late._join()
    hub.flush()
    assert len(_option_buttons(late.page)) == 4


# ==================================================================== servidor
class FakePubSub:
    def __init__(self) -> None:
        self.topics: list[str] = []

    def subscribe_topic(self, topic: str, handler: Any) -> None:
        self.topics.append(topic)

    def send_all_on_topic(self, topic: str, message: Any) -> None:
        pass

    def unsubscribe_all(self) -> None:
        pass


def _open(route: str, client_ip: str) -> FakePage:
    page = FakePage(1280, 720)
    page.route, page.client_ip = route, client_ip  # type: ignore[attr-defined]
    page.session = SimpleNamespace(id=f"s-{route}-{client_ip}")  # type: ignore[attr-defined]
    page.pubsub = FakePubSub()  # type: ignore[attr-defined]
    page.title = ""  # type: ignore[attr-defined]
    main = make_main(new_lobby(), new_quiz(), own_ips=["192.168.0.10"])
    main(page)  # type: ignore[arg-type]
    return page


def _screen_of(page: FakePage) -> Any:
    return page.on_close.__self__  # type: ignore[attr-defined]


def test_each_address_opens_its_screen() -> None:
    assert isinstance(_screen_of(_open("/?quiz=apresentar", "127.0.0.1")), QuizHost)
    assert isinstance(_screen_of(_open("/?quiz=apresentar", "192.168.0.10")), QuizHost)  # notebook pelo IP
    assert isinstance(_screen_of(_open("/?quiz=apresentar", "192.168.0.20")), QuizPhone)  # celular não vira telão
    assert isinstance(_screen_of(_open("/?quiz=jogar", "192.168.0.20")), QuizPhone)
    assert isinstance(_screen_of(_open("/?sala=GATO-42", "192.168.0.20")), RoomApp)
    assert isinstance(_screen_of(_open("/", "192.168.0.20")), RoomApp)


@pytest.fixture
def client() -> TestClient:
    return TestClient(servidor_sala.create_app("http://192.168.0.10:8000"))


def test_server_draws_the_quiz_qr_code(client: TestClient) -> None:
    qr = client.get("/qr/quiz.png")
    assert qr.status_code == 200 and qr.headers["content-type"] == "image/png"


def test_poster_links_to_the_quiz_host(client: TestClient) -> None:
    assert 'href="/?quiz=apresentar"' in client.get("/mesa").text
