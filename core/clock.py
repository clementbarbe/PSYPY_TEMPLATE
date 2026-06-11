"""
Experiment clock — single time reference for the entire session.

t=0 is defined at trigger reception. ALL timestamps everywhere
in the framework are relative to this t=0.

The underlying PsychoPy clock must be passed to the Keyboard
constructor so that key.rt uses the same reference.
"""

from __future__ import annotations

from datetime import datetime

from psychopy import core as psychopy_core


class ExperimentClock:
    """
    Wrapper around PsychoPy's core.Clock with trigger synchronisation.

    Attributes:
        trigger_wall_time: ISO wall-clock string captured at trigger reception.
    """

    def __init__(self):
        self._clock = psychopy_core.Clock()
        self.trigger_wall_time: str | None = None

    # ── Core API ─────────────────────────────────────────────────────

    @property
    def time(self) -> float:
        """Current time since last reset (trigger), in seconds."""
        return self._clock.getTime()

    def reset(self) -> None:
        """Reset to t=0 and capture wall-clock timestamp."""
        self._clock.reset()
        self.trigger_wall_time = datetime.now().strftime(
            '%Y-%m-%d_%H:%M:%S.%f'
        )

    @property
    def psychopy_clock(self) -> psychopy_core.Clock:
        """Underlying PsychoPy clock — pass this to Keyboard(clock=...)."""
        return self._clock

    # ── Utilities ────────────────────────────────────────────────────

    def wait(self, duration: float) -> None:
        """Block for *duration* seconds (uses PsychoPy's accurate wait)."""
        psychopy_core.wait(duration, hogCPUperiod=duration)

    def get_absolute_time(self) -> str:
        """Current wall-clock time as string."""
        return datetime.now().strftime('%H:%M:%S.%f')