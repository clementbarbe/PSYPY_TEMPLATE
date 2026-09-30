"""Enregistrement microphone optionnel dans un WAV standard."""

from __future__ import annotations

from typing import Any
import wave
from pathlib import Path

import numpy as np


class MicrophoneRecorder:
    """Enregistre un flux continu via ``sounddevice`` jusqu'à ``stop``."""

    def __init__(self, sample_rate: int, channels: int, logger: Any) -> None:
        """Initialise les paramètres audio sans démarrer le flux."""
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.logger = logger
        self._stream = None
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._output_path: Path | None = None

    def start(self, output_path: Path, clock: Any) -> bool:
        """Démarre l'enregistrement et retourne ``True`` en cas de succès."""
        if self._recording:
            return False
        try:
            import sounddevice as sd

            self._output_path = Path(output_path)
            self._output_path.parent.mkdir(parents=True, exist_ok=True)
            self._frames = []
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=self._callback,
            )
            self._stream.start()
            self._recording = True
            self.logger.ok(f"Microphone démarré à t={clock.time:.3f}s")
            return True
        except Exception as exc:
            self.logger.warning(f"Microphone indisponible : {exc}")
            return False

    def _callback(self, indata: Any, frames: int, time_info: Any, status: Any) -> None:
        """Copie chaque paquet audio reçu depuis le thread sounddevice."""
        del frames, time_info, status
        if self._recording:
            self._frames.append(indata.copy())

    def stop(self, clock: Any | None = None) -> Path | None:
        """Arrête le flux et écrit le WAV si des échantillons ont été reçus."""
        if not self._recording:
            return None
        self._recording = False
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None

        if not self._frames or self._output_path is None:
            return None
        audio = np.concatenate(self._frames, axis=0)
        with wave.open(str(self._output_path), "wb") as wav:
            wav.setnchannels(self.channels)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(audio.tobytes())
        timestamp = f"t={clock.time:.3f}s" if clock is not None else "cleanup"
        self.logger.ok(f"Microphone sauvegardé ({timestamp}) : {self._output_path.name}")
        return self._output_path

    def close(self) -> None:
        """Ferme proprement un enregistrement encore actif."""
        if self._recording:
            self.stop()
