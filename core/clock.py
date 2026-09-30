"""Horloge expérimentale partagée par toutes les tâches."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class ExperimentClock:
    """Encapsule l'horloge monotone PsychoPy et la référence scanner t=0.

    L'import PsychoPy est volontairement retardé jusqu'à l'instanciation afin
    que les outils de configuration et les dry-runs restent utilisables sur une
    machine sans PsychoPy.
    """

    def __init__(self) -> None:
        """Crée l’horloge PsychoPy utilisée comme référence monotone."""
        from psychopy import core

        self._core = core
        self._clock = core.Clock()
        self.trigger_wall_time: str | None = None

    @property
    def time(self) -> float:
        """Temps monotone, en secondes, depuis le dernier ``reset``."""
        return float(self._clock.getTime())

    @property
    def psychopy_clock(self) -> Any:
        """Expose l'horloge PsychoPy pour timestamping des réponses clavier."""
        return self._clock

    def reset(self) -> None:
        """Définit le trigger scanner courant comme nouvelle origine t=0."""
        self._clock.reset()
        self.trigger_wall_time = datetime.now().astimezone().isoformat(timespec="microseconds")

    def wait(self, duration: float) -> None:
        """Attend une durée positive en laissant PsychoPy gérer le CPU."""
        duration = max(0.0, float(duration))
        self._core.wait(duration, hogCPUperiod=min(duration, 0.2))
