"""Horloge expérimentale partagée par toutes les tâches."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


class ExperimentClock:
    """Encapsule l'horloge monotone PsychoPy et la référence scanner t=0.

    L'import PsychoPy est volontairement retardé jusqu'à l'instanciation afin
    que les outils de configuration et les dry-runs restent utilisables sur une
    machine sans PsychoPy.
    """

    def __init__(self) -> None:
        """Crée l’horloge PsychoPy utilisée comme référence monotone."""
        from psychopy import core, logging

        self._core = core
        self._logging = logging
        self._clock = core.Clock()
        self._origin = 0.0
        self.trigger_wall_time: str | None = None

    @property
    def time(self) -> float:
        """Temps monotone, en secondes, depuis le dernier ``reset``."""
        return self.raw_time - self._origin

    @property
    def raw_time(self) -> float:
        """Temps du clavier partagé, dont l'origine ne change jamais."""
        return float(self._clock.getTime())

    def event_time(self, timestamp: float) -> float:
        """Convertit un timestamp clavier/série dans la référence du run."""
        return float(timestamp) - self._origin

    def flip_time(self, timestamp: float) -> float:
        """Convertit le timestamp retourné par Window.flip dans le run."""
        return self.event_time(
            float(timestamp) + self._logging.defaultClock.getLastResetTime()
            - self._clock.getLastResetTime()
        )

    @property
    def psychopy_clock(self) -> Any:
        """Expose l'horloge PsychoPy pour timestamping des réponses clavier."""
        return self._clock

    def reset(self, trigger_time: float | None = None) -> None:
        """Définit le trigger scanner courant comme nouvelle origine t=0."""
        now = self.raw_time
        self._origin = now if trigger_time is None else float(trigger_time)
        wall_time = datetime.now().astimezone() - timedelta(seconds=now - self._origin)
        self.trigger_wall_time = wall_time.isoformat(timespec="microseconds")

    def wait(self, duration: float) -> None:
        """Attend une durée positive en laissant PsychoPy gérer le CPU."""
        duration = max(0.0, float(duration))
        self._core.wait(duration, hogCPUperiod=min(duration, 0.2))
