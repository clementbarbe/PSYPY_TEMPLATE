"""
Continuous microphone recording with trigger-synchronized timestamps.

Records a single WAV file for the entire session.
Start/stop times are referenced to the experiment clock (t=0 at trigger).

Uses sounddevice for low-latency recording, independent of PsychoPy audio.
Falls back gracefully if no microphone is available.
"""

from __future__ import annotations

import threading
import wave
from pathlib import Path
from datetime import datetime

import numpy as np


class MicrophoneRecorder:
    """
    Continuous WAV recorder synchronized to experiment clock.

    Usage::

        mic = MicrophoneRecorder(logger=self.logger)
        mic.start(output_path, clock)   # call right after trigger
        ...
        mic.stop()                       # call at end of session
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 1,
        dtype: str = 'int16',
        logger=None,
    ):
        self._sample_rate = sample_rate
        self._channels = channels
        self._dtype = dtype
        self._logger = logger

        self._stream = None
        self._wav_file = None
        self._recording = False
        self._output_path: Path | None = None
        self._frames: list[np.ndarray] = []

        # Timestamps relative to experiment clock
        self.start_time: float | None = None
        self.stop_time: float | None = None
        self.start_wall: str | None = None
        self.stop_wall: str | None = None

        self._sd = None
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            import sounddevice as sd
            self._sd = sd
            # Test that a default input device exists
            sd.query_devices(kind='input')
            return True
        except Exception as e:
            if self._logger:
                self._logger.warn(f"Microphone unavailable: {e}")
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self, output_path: str | Path, clock=None) -> bool:
        """
        Start continuous recording.

        Args:
            output_path: path for the output WAV file
            clock: ExperimentClock instance (for synchronized timestamps)

        Returns:
            True if recording started successfully.
        """
        if not self._available:
            if self._logger:
                self._logger.warn("Microphone not available — skipping recording.")
            return False

        if self._recording:
            if self._logger:
                self._logger.warn("Already recording.")
            return False

        self._output_path = Path(output_path)
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._frames = []

        try:
            self._stream = self._sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=self._dtype,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()
            self._recording = True

            # Timestamps
            self.start_time = clock.time if clock else 0.0
            self.start_wall = datetime.now().strftime('%H:%M:%S.%f')

            if self._logger:
                self._logger.ok(
                    f"Microphone recording started: {self._output_path.name} "
                    f"| t={self.start_time:.3f}s | {self._sample_rate}Hz"
                )
            return True

        except Exception as e:
            if self._logger:
                self._logger.err(f"Microphone start failed: {e}")
            self._recording = False
            return False

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if status and self._logger:
            self._logger.warn(f"Mic status: {status}")
        self._frames.append(indata.copy())

    def stop(self, clock=None) -> Path | None:
        """
        Stop recording and save WAV file.

        Args:
            clock: ExperimentClock for stop timestamp

        Returns:
            Path to saved WAV file, or None on failure.
        """
        if not self._recording:
            return None

        self._recording = False
        self.stop_time = clock.time if clock else 0.0
        self.stop_wall = datetime.now().strftime('%H:%M:%S.%f')

        # Stop stream
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None
        except Exception as e:
            if self._logger:
                self._logger.warn(f"Mic stream stop: {e}")

        # Save WAV
        if not self._frames:
            if self._logger:
                self._logger.warn("No audio frames recorded.")
            return None

        try:
            audio_data = np.concatenate(self._frames, axis=0)
            duration = len(audio_data) / self._sample_rate

            with wave.open(str(self._output_path), 'wb') as wf:
                wf.setnchannels(self._channels)
                wf.setsampwidth(2)  # int16 = 2 bytes
                wf.setframerate(self._sample_rate)
                wf.writeframes(audio_data.tobytes())

            if self._logger:
                self._logger.ok(
                    f"Microphone saved: {self._output_path.name} "
                    f"| {duration:.1f}s | "
                    f"t={self.start_time:.3f}–{self.stop_time:.3f}s"
                )
            self._frames = []
            return self._output_path

        except Exception as e:
            if self._logger:
                self._logger.err(f"Mic save failed: {e}")
            return None

    def close(self) -> None:
        """Force close everything. Safe to call multiple times."""
        if self._recording:
            self.stop()
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def get_sync_info(self) -> dict:
        """
        Return synchronization metadata for post-processing.

        All times relative to experiment clock t=0 (trigger).
        """
        return {
            'mic_sample_rate': self._sample_rate,
            'mic_channels': self._channels,
            'mic_start_time': self.start_time,
            'mic_stop_time': self.stop_time,
            'mic_start_wall': self.start_wall,
            'mic_stop_wall': self.stop_wall,
            'mic_duration': (
                (self.stop_time - self.start_time)
                if self.start_time is not None and self.stop_time is not None
                else None
            ),
            'mic_file': str(self._output_path) if self._output_path else '',
        }