"""Gera os efeitos sonoros do jogo em assets/sons (WAV, 44,1 kHz, 16 bits, mono).

Os sons são sintetizados aqui mesmo (só biblioteca padrão do Python): não há
arquivos de terceiros nem questões de direitos autorais. Para recriá-los ou
ajustar volume/duração, edite este arquivo e rode:

    .venv\\Scripts\\python.exe ferramentas\\gerar_sons.py
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

RATE = 44_100
OUT = Path(__file__).resolve().parents[1] / "assets" / "sons"

# Notas (Hz)
G4, C5, E5, G5, C6, E6, G6, C7 = 392.0, 523.25, 659.25, 783.99, 1046.5, 1318.5, 1568.0, 2093.0
DS4 = 311.13


def _silence(seconds: float) -> list[float]:
    return [0.0] * int(RATE * seconds)


def _tone(freq: float, seconds: float, volume: float = 0.5, *, bell: bool = True, attack: float = 0.005) -> list[float]:
    """Nota com envelope de sino (ataque curto e decaimento exponencial)."""

    n = int(RATE * seconds)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / attack) * math.exp(-t * (6.0 if bell else 3.0))
        sample = math.sin(2 * math.pi * freq * t) + 0.35 * math.sin(4 * math.pi * freq * t) + 0.12 * math.sin(6 * math.pi * freq * t)
        out.append(volume * env * sample / 1.47)
    return out


def _triangle(freq: float, seconds: float, volume: float = 0.4) -> list[float]:
    n = int(RATE * seconds)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.01) * max(0.0, 1 - t / seconds) ** 1.5
        phase = (freq * t) % 1.0
        out.append(volume * env * (4 * abs(phase - 0.5) - 1))
    return out


def _swoosh(seconds: float, volume: float = 0.35) -> list[float]:
    """Ruído suave com filtro que "abre e fecha": som de carta virando."""

    rng = random.Random(7)
    n = int(RATE * seconds)
    out, last = [], 0.0
    for i in range(n):
        t = i / seconds / RATE
        env = math.sin(math.pi * t) ** 2
        alpha = 0.08 + 0.5 * env  # filtro passa-baixa variável
        last += alpha * (rng.uniform(-1, 1) - last)
        out.append(volume * env * last * 2.2)
    return out


def _mix(*tracks: tuple[float, list[float]]) -> list[float]:
    """Soma trilhas começando em instantes diferentes: (início em s, amostras)."""

    length = max(int(start * RATE) + len(samples) for start, samples in tracks)
    out = [0.0] * length
    for start, samples in tracks:
        offset = int(start * RATE)
        for i, value in enumerate(samples):
            out[offset + i] += value
    return out


def _save(name: str, samples: list[float], peak: float = 0.7) -> None:
    top = max(abs(s) for s in samples) or 1.0
    frames = b"".join(struct.pack("<h", int(max(-1, min(1, s / top * peak)) * 32767)) for s in samples)
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(frames)
    print(f"{name}.wav  {len(samples) / RATE:.2f} s")


def main() -> None:
    # Virar carta: "fuu" curto + tique.
    _save("virar", _mix((0, _swoosh(0.11)), (0.07, _tone(2400, 0.05, 0.25))), peak=0.45)
    # Par encontrado / questão certa: arpejo de sino (dó–mi–sol agudo).
    _save("acerto", _mix((0, _tone(C6, 0.35)), (0.07, _tone(E6, 0.35)), (0.14, _tone(G6, 0.5))), peak=0.6)
    # Erro: duas notas descendentes, suaves (sem soar como "castigo").
    _save("erro", _mix((0, _triangle(G4, 0.14)), (0.13, _triangle(DS4, 0.22))), peak=0.45)
    # Incentivo (Desafio Relâmpago certo): fanfarra curta + brilho.
    fanfare = [(0.00, _tone(C5, 0.25)), (0.08, _tone(E5, 0.25)), (0.16, _tone(G5, 0.25)), (0.24, _tone(C6, 0.7, bell=False))]
    chord = [(0.24, _tone(E5, 0.7, 0.35, bell=False)), (0.24, _tone(G5, 0.7, 0.35, bell=False))]
    sparkle = [(0.40, _tone(E6 * 2, 0.2, 0.18)), (0.48, _tone(G6 * 2, 0.2, 0.18)), (0.56, _tone(C7 * 2, 0.25, 0.15))]
    _save("incentivo", _mix(*fanfare, *chord, *sparkle), peak=0.65)
    # Vitória (fim da partida/fase): fanfarra mais longa.
    intro = [(0.00, _tone(G4, 0.2)), (0.10, _tone(C5, 0.2)), (0.20, _tone(E5, 0.2)), (0.30, _tone(G5, 0.2))]
    final = [(0.42, _tone(n, 1.1, 0.4, bell=False)) for n in (C5, E5, G5, C6)]
    stars = [(0.6 + k * 0.09, _tone(f, 0.25, 0.15)) for k, f in enumerate((C7, G6 * 2, E6 * 2, C7 * 2))]
    _save("vitoria", _mix(*intro, *final, *stars), peak=0.65)


if __name__ == "__main__":
    main()
