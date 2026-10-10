"""Persistência local das preferências do jogo.

Os dados ficam em um arquivo JSON no diretório de dados do aplicativo. Quando
empacotado com ``flet build`` (Android, iOS, desktop), o Flet informa esse
diretório pela variável ``FLET_APP_STORAGE_DATA``; ao rodar a partir do código
fonte, usa-se ``~/.mente_financeira``.

Nenhum dado pessoal é gravado (seção 5.9 do projeto): apenas preferências de
aparência e as medalhas conquistadas no aparelho.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mente_financeira.admin import admin_ativo

SETTINGS_FILE = "settings.json"


def default_data_dir() -> Path:
    configured = os.getenv("FLET_APP_STORAGE_DATA")
    base = Path(configured) if configured else Path.home() / ".mente_financeira"
    # O modo administrador não mexe nas preferências usadas pelos alunos.
    return base / "admin" if admin_ativo() else base


@dataclass(slots=True)
class Settings:
    palette: str = "kids"
    dark_mode: bool = False
    sound: bool = True  # efeitos sonoros ligados
    medals: list[str] = field(default_factory=list)  # chaves das medalhas (core/medals.py)


class SettingsStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.path = (data_dir or default_data_dir()) / SETTINGS_FILE
        # No site, cada gravação também vai para o armazenamento do navegador
        # (veja connect_browser_storage).
        self.on_save: Callable[[str], None] | None = None

    def load(self) -> Settings:
        """Lê as preferências; arquivo ausente ou corrompido gera o padrão."""

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return Settings()
        if not isinstance(raw, dict):
            return Settings()
        defaults = Settings()
        values = {}
        for item in fields(Settings):
            value = raw.get(item.name)
            default = getattr(defaults, item.name)
            if type(value) is not type(default):
                value = default
            elif isinstance(value, list):
                value = list(dict.fromkeys(v for v in value if isinstance(v, str)))
            values[item.name] = value
        return Settings(**values)

    def save(self, settings: Settings) -> bool:
        """Grava as preferências. Uma falha de disco não interrompe o jogo."""

        text = json.dumps(asdict(settings), ensure_ascii=False, indent=2)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            return False
        if self.on_save is not None:
            try:
                self.on_save(text)
            except Exception:
                pass  # preferência é conforto: nunca interrompe o jogo
        return True


BROWSER_KEY = "mente_financeira.settings"


async def connect_browser_storage(store: SettingsStore, preferences: Any, run_task: Callable[..., Any]) -> None:
    """Liga as preferências ao armazenamento do navegador (jogo publicado na web).

    No site, o Python roda dentro da página e o arquivo de preferências existe
    só na memória: some ao fechar a aba. Aqui o conteúdo salvo no navegador é
    restaurado para o arquivo e, a cada gravação, enviado de volta.

    ``preferences`` é o serviço ``ft.SharedPreferences()``; ``run_task`` é
    ``page.run_task``.
    """

    try:
        saved = await preferences.get(BROWSER_KEY)
    except Exception:
        saved = None
    if isinstance(saved, str) and saved.strip():
        try:
            store.path.parent.mkdir(parents=True, exist_ok=True)
            store.path.write_text(saved, encoding="utf-8")
        except OSError:
            pass
    store.on_save = lambda text: run_task(preferences.set, BROWSER_KEY, text)
