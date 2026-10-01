"""Efeitos sonoros (virar carta, acerto, erro, incentivo, vitória).

Os arquivos ficam em assets/sons e são gerados por ferramentas/gerar_sons.py.
O som toca pelo cliente do Flet (flet-audio), sem travar o jogo. O botão 🔊/🔇
liga e desliga os efeitos, e a escolha é lembrada entre as sessões.
"""

from __future__ import annotations

from typing import Any

import flet as ft

from mente_financeira.storage import SettingsStore

SOUNDS = ("virar", "acerto", "erro", "incentivo", "vitoria")

try:  # o jogo continua funcionando (sem som) se o flet-audio faltar
    from flet_audio import Audio
except ImportError:  # pragma: no cover
    Audio = None  # type: ignore[assignment,misc]


class SoundEffects:
    def __init__(self, page: ft.Page, store: SettingsStore) -> None:
        self.page = page
        self.store = store
        self.enabled = store.load().sound
        self.history: list[str] = []  # sons pedidos (usado pelos testes)
        self._audios: dict[str, Any] = {}
        self._buttons: list[ft.IconButton] = []

    def preload(self) -> None:
        """Registra os áudios na página antes do primeiro uso (evita atraso)."""

        services = getattr(self.page, "services", None)
        if Audio is None or services is None:
            return
        for name in SOUNDS:
            if name not in self._audios:
                audio = Audio(src=f"sons/{name}.wav", autoplay=False, volume=0.9)
                services.append(audio)
                self._audios[name] = audio

    def play(self, name: str) -> None:
        if not self.enabled or name not in SOUNDS:
            return
        self.history.append(name)
        if name in self._audios:
            self.page.run_task(self._play, name)

    async def _play(self, name: str) -> None:
        try:
            await self._audios[name].play(0)
        except Exception:
            pass  # som é enfeite: uma falha nunca interrompe o jogo

    # ------------------------------------------------------------ botão
    def toggle(self, _: Any = None) -> None:
        self.enabled = not self.enabled
        settings = self.store.load()
        settings.sound = self.enabled
        self.store.save(settings)
        for button in self._buttons:
            self._paint(button)
        self.page.update()
        if self.enabled:
            self.play("virar")  # confirma que o som voltou

    def button(self, color: str) -> ft.IconButton:
        button = ft.IconButton(on_click=self.toggle, icon_color=color)
        self._paint(button)
        # Cada tela redesenhada cria outro botão; basta lembrar dos mais recentes.
        self._buttons = self._buttons[-4:] + [button]
        return button

    def _paint(self, button: ft.IconButton) -> None:
        button.icon = ft.Icons.VOLUME_UP_ROUNDED if self.enabled else ft.Icons.VOLUME_OFF_ROUNDED
        button.tooltip = "Som ligado (clique para desligar)" if self.enabled else "Som desligado (clique para ligar)"
