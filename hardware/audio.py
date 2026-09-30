"""Audio PsychoPy préchargé avec scheduling Psychtoolbox si disponible."""

from __future__ import annotations

from typing import Any
from pathlib import Path


class AudioManager:
    """Précharge les sons et expose lecture immédiate ou planifiée."""

    _configured = False

    def __init__(self, settings: Any, logger: Any) -> None:
        """Configure le backend audio et prépare le registre des sons."""
        self.settings = settings
        self.logger = logger
        self.sounds: dict[str, object] = {}
        self._configure_backend()
        from psychopy import sound

        self._sound_class = sound.Sound

    def _configure_backend(self) -> None:
        """Configure une seule fois le backend audio PsychoPy."""
        if AudioManager._configured:
            return
        try:
            from psychopy import prefs

            prefs.hardware["audioLib"] = [self.settings.audio_backend]
            AudioManager._configured = True
        except Exception as exc:
            self.logger.warning(f"Configuration audio impossible : {exc}")

    def preload_tone(
        self,
        name: str,
        frequency: float,
        duration: float,
        volume: float = 1.0,
    ) -> None:
        """Précharge un son pur identifié par ``name``."""
        sound = self._sound_class(
            value=frequency,
            secs=duration,
            sampleRate=self.settings.audio_sample_rate,
            stereo=True,
        )
        sound.setVolume(volume)
        self.sounds[name] = sound

    def preload_file(self, name: str, path: Path, volume: float = 1.0) -> None:
        """Précharge un fichier audio."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        sound = self._sound_class(
            value=str(path),
            sampleRate=self.settings.audio_sample_rate,
            stereo=True,
        )
        sound.setVolume(volume)
        self.sounds[name] = sound

    def play_now(self, name: str) -> None:
        """Joue immédiatement un son préchargé."""
        self._sound(name).play()

    def play_scheduled(self, name: str, target_time: float, clock: Any) -> float:
        """Planifie un son et retourne l'onset expérimental prévu/utilisé."""
        sound = self._sound(name)
        delay = target_time - clock.time
        if delay < self.settings.audio_minimum_schedule_lead_seconds:
            sound.play()
            return clock.time
        absolute = self._absolute_time(delay)
        if absolute is None:
            sound.play()
            return clock.time
        sound.play(when=absolute)
        return target_time

    def _absolute_time(self, delay: float) -> float | None:
        """Convertit un délai relatif en temps Psychtoolbox absolu."""
        try:
            from psychtoolbox import GetSecs

            return float(GetSecs() + delay)
        except Exception:
            return None

    def _sound(self, name: str) -> Any:
        """Retourne un son préchargé ou lève une erreur explicite."""
        try:
            return self.sounds[name]
        except KeyError as exc:
            raise KeyError(f"Son non préchargé : {name!r}") from exc

    def close(self) -> None:
        """Arrête et oublie les sons préchargés."""
        for sound in self.sounds.values():
            try:
                sound.stop()
            except Exception:
                pass
        self.sounds.clear()
