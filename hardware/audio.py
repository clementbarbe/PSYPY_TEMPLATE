"""
Audio stimulus manager with precise PTB scheduling.

Provides:
    - Preloading audio files (zero-latency at playback)
    - Scheduled playback (~100ms lead, PTB handles precision)
    - Sub-millisecond onset accuracy with PTB backend

Architecture:
    PsychoPy's PTB (PsychToolbox) audio backend supports
    snd.play(when=absolute_time), which tells PortAudio to start
    the audio stream at a precise hardware clock time.

    The workflow for a task:
        1. At init:   audio.preload('beep', 'stimuli/sounds/beep.wav')
        2. In trial:  audio.play_scheduled('beep', target_time, clock)
           (call this ~100ms BEFORE target_time)
        3. PTB buffers the audio and starts it at exactly target_time

Usage in a task::

    def _setup_stimuli(self):
        self.audio.preload('tone', 'stimuli/sounds/tone.wav')

    def run_trial(self, ...):
        # 100ms before we need the sound
        target = self.clock.time + 0.100
        self.audio.play_scheduled('tone', target, self.clock)

        # Show visual at the same time
        self.win.flip()
"""

from __future__ import annotations

from pathlib import Path

from config.constants import (
    AUDIO_BACKEND,
    AUDIO_SAMPLE_RATE,
    AUDIO_SCHEDULE_LEAD,
    AUDIO_MIN_LEAD,
)


class AudioManager:
    """
    Precise audio playback with preloading and PTB scheduling.

    Thread-unsafe (PsychoPy is single-threaded).
    """

    _backend_configured = False

    def __init__(self, backend: str = AUDIO_BACKEND):
        """
        Configure audio backend and initialise.

        Args:
            backend: 'ptb' (recommended), 'sounddevice', or 'pygame'.
        """
        self._sounds: dict[str, object] = {}
        self._backend_name = backend

        # Configure PsychoPy prefs BEFORE importing sound
        if not AudioManager._backend_configured:
            self._configure_backend(backend)

        # Now import (safe — prefs are set)
        from psychopy import sound
        self._sound_module = sound
        self._Sound = sound.Sound

    @staticmethod
    def _configure_backend(backend: str) -> None:
        """Set PsychoPy audio preferences. Must happen before sound import."""
        try:
            from psychopy import prefs
            prefs.hardware['audioLib'] = [backend]
            AudioManager._backend_configured = True
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════
    # Preloading
    # ═════════════════════════════════════════════════════════════════

    def preload(self, name: str, filepath: str | Path,
                volume: float = 1.0) -> None:
        """
        Load an audio file into memory.

        The file is decoded and buffered — playback will have
        zero loading latency. Call this during task setup.

        Args:
            name: identifier for this sound
            filepath: path to .wav, .ogg, or .mp3 file
            volume: 0.0 to 1.0
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        snd = self._Sound(
            value=str(filepath),
            sampleRate=AUDIO_SAMPLE_RATE,
            stereo=True,
        )
        snd.setVolume(volume)
        self._sounds[name] = snd

    def preload_many(self, sounds: dict[str, str | Path],
                     volume: float = 1.0) -> None:
        """
        Preload multiple sounds.

        Args:
            sounds: {name: filepath} dict
            volume: default volume for all
        """
        for name, filepath in sounds.items():
            self.preload(name, filepath, volume)

    def preload_tone(self, name: str, frequency: float = 440.0,
                     duration: float = 0.2, volume: float = 1.0) -> None:
        """
        Create and preload a pure tone.

        Args:
            name: identifier
            frequency: Hz (440 = A4)
            duration: seconds
            volume: 0.0 to 1.0
        """
        snd = self._Sound(
            value=frequency,
            secs=duration,
            sampleRate=AUDIO_SAMPLE_RATE,
            stereo=True,
        )
        snd.setVolume(volume)
        self._sounds[name] = snd

    # ═════════════════════════════════════════════════════════════════
    # Playback
    # ═════════════════════════════════════════════════════════════════

    def play_now(self, name: str) -> float:
        """
        Play a preloaded sound immediately.

        Less precise than play_scheduled — use only when
        exact timing is not critical.

        Returns:
            Approximate onset time (from PsychoPy clock).
        """
        if name not in self._sounds:
            raise KeyError(f"Sound '{name}' not preloaded.")

        from psychopy.core import getTime
        self._sounds[name].play()
        return getTime()

    def play_scheduled(self, name: str, target_time: float,
                       clock) -> float:
        """
        Schedule playback at a precise experiment clock time.

        MUST be called BEFORE target_time (ideally ~100ms before).
        PTB will buffer the audio and start it at exactly target_time.

        Args:
            name: identifier of a preloaded sound
            target_time: desired onset in experiment clock (clock.time)
            clock: ExperimentClock instance (for time reference)

        Returns:
            The scheduled onset time (same as target_time if valid,
            or actual onset if played immediately).

        Example::

            # In your trial loop, ~100ms before target:
            target = self.clock.time + 0.100
            onset = self.audio.play_scheduled('beep', target, self.clock)

            # Visual flip at approximately the same time:
            stim.draw()
            self.win.flip()
        """
        if name not in self._sounds:
            raise KeyError(f"Sound '{name}' not preloaded.")

        snd = self._sounds[name]

        # How far in the future?
        now_exp = clock.time
        delay = target_time - now_exp

        if delay < AUDIO_MIN_LEAD:
            # Too late for scheduling — play immediately
            snd.play()
            return now_exp

        # Get absolute time for PTB scheduling
        abs_target = self._get_absolute_target(delay)

        if abs_target is not None:
            snd.play(when=abs_target)
            return target_time
        else:
            # Fallback: no PTB, play immediately
            snd.play()
            return now_exp

    def _get_absolute_target(self, delay: float) -> float | None:
        """
        Convert a relative delay to an absolute PTB timestamp.

        Tries psychtoolbox.GetSecs first (exact PTB clock),
        falls back to psychopy.core.getTime.
        """
        try:
            from psychtoolbox import GetSecs
            return GetSecs() + delay
        except ImportError:
            pass

        try:
            from psychopy.core import getTime
            return getTime() + delay
        except ImportError:
            pass

        return None

    # ═════════════════════════════════════════════════════════════════
    # Control
    # ═════════════════════════════════════════════════════════════════

    def stop(self, name: str) -> None:
        """Stop a playing sound."""
        if name in self._sounds:
            try:
                self._sounds[name].stop()
            except Exception:
                pass

    def stop_all(self) -> None:
        """Stop all playing sounds."""
        for snd in self._sounds.values():
            try:
                snd.stop()
            except Exception:
                pass

    def is_loaded(self, name: str) -> bool:
        """Check if a sound is preloaded."""
        return name in self._sounds

    @property
    def loaded_sounds(self) -> list[str]:
        """List of preloaded sound names."""
        return list(self._sounds.keys())

    def close(self) -> None:
        """Stop and release all sounds."""
        self.stop_all()
        self._sounds.clear()