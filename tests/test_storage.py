from pathlib import Path

from mente_financeira.storage import Settings, SettingsStore


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


def test_storage_dir_comes_from_flet(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    assert SettingsStore().path == tmp_path / "settings.json"
