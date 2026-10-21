"""Faz o site publicado sempre baixar a versão mais nova do jogo.

No site, o Python roda no navegador e baixa o jogo inteiro num pacote
(assets/app/app.zip). O navegador guarda esse pacote por alguns minutos, e o
Ctrl+F5 não o renova (quem baixa é o Python, não a página). Assim, logo depois
de uma publicação, quem já tinha aberto o site continuava vendo a versão antiga.

Este script ajusta o python-worker.js do site construído para baixar o pacote
com ``cache: "no-cache"``: a cada abertura o navegador confere se o pacote
mudou e só baixa de novo quando mudou. Roda na publicação, depois do
``flet build web`` (.github/workflows/publicar-site.yml):

    python ferramentas/site_sem_cache.py build/web
"""

from __future__ import annotations

from pathlib import Path
import sys

ORIGINAL = "await pyfetch(app_package_url)"
SEM_CACHE = 'await pyfetch(app_package_url, cache="no-cache")'


def sem_cache(worker_js: str) -> str:
    """O python-worker.js com o download do pacote do jogo sem cache."""

    if SEM_CACHE in worker_js:
        return worker_js
    if worker_js.count(ORIGINAL) != 1:
        raise ValueError(f"python-worker.js mudou: não achei '{ORIGINAL}' (uma vez só).")
    return worker_js.replace(ORIGINAL, SEM_CACHE)


def main(site: Path) -> None:
    worker = site / "python-worker.js"
    worker.write_text(sem_cache(worker.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"{worker}: pacote do jogo baixado sem cache.")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "build/web"))
