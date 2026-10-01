"""Persistência local das preferências do jogo.

Os dados ficam em um arquivo JSON no diretório de dados do aplicativo. Quando
empacotado com ``flet build`` (Android, iOS, desktop), o Flet informa esse
diretório pela variável ``FLET_APP_STORAGE_DATA``; ao rodar a partir do código
fonte, usa-se ``~/.mente_financeira``.

Nenhum dado pessoal é gravado (seção 5.9 do projeto): apenas preferências de
aparência.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
import os
from pathlib import Path

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


class SettingsStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.path = (data_dir or default_data_dir()) / SETTINGS_FILE

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
        for field in fields(Settings):
            value = raw.get(field.name)
            default = getattr(defaults, field.name)
            values[field.name] = value if type(value) is type(default) else default
        return Settings(**values)

    def save(self, settings: Settings) -> bool:
        """Grava as preferências. Uma falha de disco não interrompe o jogo."""

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            return False
        return True
