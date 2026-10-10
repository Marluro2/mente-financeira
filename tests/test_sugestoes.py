"""Botão "Deixe sua sugestão": formulário no site e no Duelo em sala."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random
from typing import Any

import flet as ft
import pytest
from fastapi.testclient import TestClient

from fakes import FakePage, walk
from mente_financeira import sugestoes
from mente_financeira.sala.app import RoomApp, new_lobby
from mente_financeira.storage import SettingsStore
from mente_financeira.sugestoes import Suggestion, SuggestionBox, SuggestionError, make_suggestion
from mente_financeira.ui.shell import GameShell
from mente_financeira.ui.suggestion_form import SUGGESTION_QR, SuggestionForm
import servidor_sala


class NoMessenger:
    def subscribe(self, *_: Any) -> None: ...

    def send(self, *_: Any) -> None: ...

    def close(self) -> None: ...


def _button(page: FakePage) -> ft.OutlinedButton | None:
    return next(
        (c for c in walk(page.controls[-1]) if isinstance(c, ft.OutlinedButton) and c.content == "Deixe sua sugestão"),
        None,
    )


# ------------------------------------------------------------------ regras
def test_suggestion_needs_text_and_optional_fields_are_checked() -> None:
    assert make_suggestion("  Mais   fases  ") == Suggestion("Mais fases")
    assert make_suggestion("Mais fases", "Ensino Médio", "15") == Suggestion("Mais fases", "Ensino Médio", 15)
    for kwargs in ({"text": ""}, {"text": "x" * 501}, {"text": "ok ok", "level": "Faculdade"}, {"text": "ok ok", "age": "dez"}, {"text": "ok ok", "age": "3"}):
        with pytest.raises(SuggestionError):
            make_suggestion(**kwargs)


def test_box_writes_a_csv_that_excel_opens(tmp_path: Path) -> None:
    box = SuggestionBox(tmp_path / "sugestoes" / "sugestoes.csv")
    box.save(Suggestion("Mais fases; com cartas", "Ensino Fundamental 1", 9), when=datetime(2026, 10, 8, 14, 30))
    box.save(Suggestion("Modo noturno"))
    assert box.path.read_bytes().startswith(b"\xef\xbb\xbf")  # acentos certos no Excel
    rows = box.read()
    assert rows[0] == {"data_hora": "08/10/2026 14:30", "sugestao": "Mais fases; com cartas", "nivel": "Ensino Fundamental 1", "idade": "9"}
    assert rows[1]["sugestao"] == "Modo noturno" and rows[1]["idade"] == ""


# ------------------------------------------------------------------ site
def test_site_button_appears_only_with_a_form(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shell = GameShell(FakePage(1280, 720), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    assert sugestoes.FORM_URL == "" or _button(shell.page) is not None
    monkeypatch.setattr(sugestoes, "FORM_URL", "https://forms.gle/exemplo")
    for size in ((1280, 720), (360, 740)):
        shell = GameShell(FakePage(*size), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
        button = _button(shell.page)
        assert button is not None
        button.on_click(None)
        assert shell.page.tasks[-1] == (shell.page.launch_url, ("https://forms.gle/exemplo",))


def test_site_without_form_has_no_button(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sugestoes, "FORM_URL", "")
    shell = GameShell(FakePage(1280, 720), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    assert _button(shell.page) is None


# ------------------------------------------------------------------ feira
def test_room_form_saves_to_the_notebook(tmp_path: Path) -> None:
    box = SuggestionBox(tmp_path / "sugestoes.csv")
    page = FakePage(390, 844)
    RoomApp(page, new_lobby(), NoMessenger(), player_id="a", on_suggestion=box.save)  # type: ignore[arg-type]
    _button(page).on_click(None)
    form = page.dialogs[-1]
    assert isinstance(form, ft.AlertDialog) and form.title.value == "Deixe sua sugestão 💡"
    labels = [c.label for c in walk(form) if isinstance(c, (ft.TextField, ft.Dropdown))]
    assert labels == ["Sua sugestão", "Nível (opcional)", "Idade (opcional)"]  # sem nome nem contato
    text, level, age = [c for c in walk(form) if isinstance(c, (ft.TextField, ft.Dropdown))]

    send = next(b for b in form.actions if b.content == "Enviar")
    send.on_click(None)
    assert text.error and not box.path.exists()  # sugestão é obrigatória

    text.value, level.value, age.value = "Colocar mais cartas", "Ensino Fundamental 2", "12"
    send.on_click(None)
    assert box.read()[0]["sugestao"] == "Colocar mais cartas" and box.read()[0]["idade"] == "12"
    assert isinstance(page.dialogs[-1], ft.SnackBar) and form not in page.dialogs


def test_server_wires_the_box(tmp_path: Path) -> None:
    box = SuggestionBox(tmp_path / "s.csv")
    client = TestClient(servidor_sala.create_app("http://192.168.0.10:8000", suggestions=box))
    assert client.get("/").status_code == 200


def test_form_age_error_goes_to_age_field() -> None:
    page = FakePage(390, 844)
    form = SuggestionForm(page, lambda _: None)  # type: ignore[arg-type]
    form.text.value, form.age.value = "Boa ideia", "200"
    form._send()
    assert form.age.error and not form.text.error


def test_site_uses_the_project_form_and_shows_its_qr(tmp_path: Path) -> None:
    assert sugestoes.FORM_URL == "https://forms.gle/wh7rXXBcUBLCn7857"
    assert (Path(__file__).resolve().parent.parent / "assets" / SUGGESTION_QR).stat().st_size > 200
    shell = GameShell(FakePage(1280, 720), store=SettingsStore(tmp_path), rng=random.Random(2))  # type: ignore[arg-type]
    assert _button(shell.page) is not None
    images = [c.src for c in walk(shell.page.controls[-1]) if isinstance(c, ft.Image)]
    assert SUGGESTION_QR in images


def test_room_start_screen_shows_the_qr_too(tmp_path: Path) -> None:
    page = FakePage(390, 844)
    RoomApp(page, new_lobby(), NoMessenger(), player_id="a", on_suggestion=SuggestionBox(tmp_path / "s.csv").save)  # type: ignore[arg-type]
    assert SUGGESTION_QR in [c.src for c in walk(page.controls[-1]) if isinstance(c, ft.Image)]


def test_qr_image_matches_the_form_address() -> None:
    import segno

    expected = segno.make(sugestoes.FORM_URL, error="m")
    rows = len(expected.matrix) + 4  # borda de 2 módulos de cada lado
    png = (Path(__file__).resolve().parent.parent / "assets" / SUGGESTION_QR).read_bytes()
    width = int.from_bytes(png[16:20], "big")
    assert width == rows * 10  # mesmo tamanho do QR desse endereço (escala 10)
