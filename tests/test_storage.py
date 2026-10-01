import asyncio
from pathlib import Path

from mente_financeira.storage import BROWSER_KEY, Settings, SettingsStore, connect_browser_storage


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    assert SettingsStore(tmp_path).load() == Settings()


def test_settings_round_trip(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "novo")
    assert store.save(Settings(palette="neon", dark_mode=True))
    assert store.load() == Settings(palette="neon", dark_mode=True)


def test_corrupted_or_wrong_types_fall_back_to_defaults(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path)
    store.path.write_text("{ isto não é json", encoding="utf-8")
    assert store.load() == Settings()
    store.path.write_text('{"palette": 3, "dark_mode": true}', encoding="utf-8")
    assert store.load() == Settings(palette="kids", dark_mode=True)
    store.path.write_text("[1, 2]", encoding="utf-8")
    assert store.load() == Settings()


class _FakeBrowserPrefs:
    """Imita ft.SharedPreferences (armazenamento do navegador)."""

    def __init__(self, initial: dict | None = None) -> None:
        self.data = dict(initial or {})

    async def get(self, key: str):
        return self.data.get(key)

    async def set(self, key: str, value: str) -> bool:
        self.data[key] = value
        return True


def _run_now(handler, *args) -> None:
    asyncio.run(handler(*args))


def test_browser_storage_restores_and_mirrors_settings(tmp_path: Path) -> None:
    saved = '{"palette": "neon", "dark_mode": true, "sound": false}'
    prefs = _FakeBrowserPrefs({BROWSER_KEY: saved})
    store = SettingsStore(tmp_path / "memoria")
    asyncio.run(connect_browser_storage(store, prefs, _run_now))
    assert store.load() == Settings(palette="neon", dark_mode=True, sound=False)  # restaurado

    store.save(Settings(palette="pastel"))
    assert '"pastel"' in prefs.data[BROWSER_KEY]  # espelhado no navegador


def test_browser_storage_survives_empty_or_broken_browser(tmp_path: Path) -> None:
    class Broken(_FakeBrowserPrefs):
        async def get(self, key: str):
            raise RuntimeError("armazenamento bloqueado")

    store = SettingsStore(tmp_path)
    asyncio.run(connect_browser_storage(store, Broken(), _run_now))
    assert store.load() == Settings()

    def failing_task(*_):
        raise RuntimeError("sem conexão")

    asyncio.run(connect_browser_storage(store, _FakeBrowserPrefs(), failing_task))
    assert store.save(Settings(sound=False))  # a falha do navegador não impede o jogo


def test_storage_dir_comes_from_flet(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    assert SettingsStore().path == tmp_path / "settings.json"
