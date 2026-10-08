"""Endereço do servidor online e consulta de quem está online.

O site do GitHub Pages pergunta ao servidor, de tempos em tempos, quantas
pessoas estão no modo online em cada trilha (``/api/online``). Enquanto
``SERVER_URL`` estiver vazio, o site não mostra nada do modo online.
"""

from __future__ import annotations

import asyncio
import json
import sys
import urllib.request

# Endereço público do servidor (ex.: "https://mente-financeira-online.onrender.com").
# Fica vazio até o servidor ser publicado; aí o site passa a mostrar o modo online.
SERVER_URL = ""

COUNTS_PATH = "/api/online"
TIMEOUT_SECONDS = 8


def online_enabled(url: str | None = None) -> bool:
    return bool(SERVER_URL if url is None else url)


def play_url(track: str, url: str | None = None) -> str:
    """Endereço da sala de espera, já na trilha escolhida."""

    base = (SERVER_URL if url is None else url).rstrip("/")
    return f"{base}/?trilha={track}"


def parse_counts(data: object) -> dict[str, int]:
    if not isinstance(data, dict):
        return {}
    return {str(k): int(v) for k, v in data.items() if isinstance(v, int) and v >= 0}


async def fetch_counts(url: str | None = None) -> dict[str, int] | None:
    """Pessoas online por trilha, ou None se o servidor não respondeu
    (por exemplo, enquanto ele ainda está acordando)."""

    base = (SERVER_URL if url is None else url).rstrip("/")
    if not base:
        return None
    address = base + COUNTS_PATH
    try:
        if sys.platform == "emscripten":  # site publicado: o Python roda no navegador
            from pyodide.http import pyfetch  # type: ignore[import-not-found]

            response = await asyncio.wait_for(pyfetch(address), TIMEOUT_SECONDS)
            if not response.ok:
                return None
            return parse_counts(await response.json())

        def read() -> object:
            with urllib.request.urlopen(address, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 - endereço fixo
                return json.loads(response.read().decode("utf-8"))

        return parse_counts(await asyncio.to_thread(read))
    except Exception:  # sem internet, servidor dormindo etc.: só não mostra a contagem
        return None
