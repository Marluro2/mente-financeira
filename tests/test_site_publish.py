"""Publicação do site: o pacote do jogo é baixado sem cache (ferramentas/site_sem_cache.py)."""

from importlib import util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = util.spec_from_file_location("site_sem_cache", ROOT / "ferramentas" / "site_sem_cache.py")
site_sem_cache = util.module_from_spec(spec)
spec.loader.exec_module(site_sem_cache)


def test_flet_worker_still_downloads_the_game_the_same_way() -> None:
    """Se uma versão nova do Flet mudar o python-worker.js, a publicação avisa aqui antes."""

    flet_web = pytest.importorskip("flet_web")
    worker = (Path(flet_web.__file__).parent / "web" / "python-worker.js").read_text(encoding="utf-8")
    patched = site_sem_cache.sem_cache(worker)
    assert patched.count(site_sem_cache.SEM_CACHE) == 1
    assert site_sem_cache.sem_cache(patched) == patched  # rodar duas vezes não estraga


def test_publishing_rewrites_the_built_site(tmp_path: Path) -> None:
    (tmp_path / "python-worker.js").write_text("response = await pyfetch(app_package_url)\n", encoding="utf-8")
    site_sem_cache.main(tmp_path)
    assert 'pyfetch(app_package_url, cache="no-cache")' in (tmp_path / "python-worker.js").read_text(encoding="utf-8")


def test_unknown_worker_is_refused() -> None:
    with pytest.raises(ValueError, match="python-worker.js mudou"):
        site_sem_cache.sem_cache("fetch(outra_coisa)")
