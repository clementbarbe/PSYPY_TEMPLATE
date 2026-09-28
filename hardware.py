"""
Matériel optionnel regroupé dans un seul fichier.

Contient :
- trigger clavier ou série ;
- marqueurs TTL parallèle ou série ;
- audio PsychoPy/PTB ;
- EyeLink optionnel ;
- microphone optionnel.

Toutes les dépendances matérielles sont optionnelles :
une expérience locale sans matériel doit fonctionner.
"""

from __future__ import annotations

import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np


class Hardware:
    """API matérielle compacte utilisée par les tâches."""

    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger

        self._marker_device = None
        self._trigger_serial = None
        self._audio = None
        self._eyetracker = None
        self._microphone = None
        self._closed = False

        self._init_markers()
        self._init_trigger_serial()

        if settings.eyetracker_enabled:
            self._init_eyetracker()

    # ------------------------------------------------------------------
    # Trigger entrant
    # ------------------------------------------------------------------

    def wait_for_trigger(self, keyboard, quit_key: str) -> bool:
        """
        Attend un trigger.

        Retourne True si reçu.
        Lève KeyboardInterrupt si Escape est pressé.
        """
        if not self.settings.trigger_enabled:
            return True

        source = self.settings.trigger_source.lower()

        if source == "serial" and self._trigger_serial is not None:
            return self._wait_serial_trigger()

        deadline = time.monotonic() + self.settings.trigger_timeout_seconds
        trigger_key = self.settings.trigger_key

        while time.monotonic() < deadline:
            keys = keyboard.getKeys(
                keyList=[trigger_key, quit_key],
                waitRelease=False,
            )

            for key in keys:
                if key.name == quit_key:
                    raise KeyboardInterrupt("Abort during trigger wait")

                if key.name == trigger_key:
                    return True

        return False

    def _init_trigger_serial(self) -> None:
        if not self.settings.trigger_enabled:
            return

        if self.settings.trigger_source.lower() != "serial":
            return

        port_name = self.settings.trigger_serial_port

        if not port_name:
            self.logger.warning(
                "Trigger série activé mais aucun serial_port configuré."
            )
            return

        try:
            import serial

            self._trigger_serial = serial.Serial(
                port=port_name,
                baudrate=self.settings.trigger_baudrate,
                timeout=0.001,
            )

            self.logger.ok(f"Trigger série connecté : {port_name}")

        except Exception as exc:
            self.logger.warning(f"Trigger série indisponible : {exc}")
            self._trigger_serial = None

    def _wait_serial_trigger(self) -> bool:
        deadline = time.monotonic() + self.settings.trigger_timeout_seconds

        while time.monotonic() < deadline:
            try:
                if self._trigger_serial.in_waiting:
                    self._trigger_serial.read(1)
                    return True
            except Exception:
                return False

            time.sleep(0.001)

        return False

    # ------------------------------------------------------------------
    # Marqueurs TTL / série
    # ------------------------------------------------------------------

    def _init_markers(self) -> None:
        if not self.settings.markers_enabled:
            return

        transport = self.settings.marker_transport.lower()

        if transport == "parallel":
            self._init_parallel_port()

        elif transport == "serial":
            self._init_marker_serial()

        else:
            self.logger.info("Marqueurs désactivés (transport=none).")

    def _init_parallel_port(self) -> None:
        address = self.settings.parallel_address

        if address is None:
            self.logger.warning("Port parallèle activé sans adresse.")
            return

        try:
            from psychopy import parallel

            self._marker_device = parallel.ParallelPort(address=address)
            self._marker_device.setData(0)
            self.logger.ok(f"Port parallèle actif : {hex(int(address))}")

        except Exception as exc:
            self.logger.warning(f"Port parallèle indisponible : {exc}")
            self._marker_device = None

    def _init_marker_serial(self) -> None:
        port_name = self.settings.marker_serial_port

        if not port_name:
            self.logger.warning("Marqueurs série activés sans serial_port.")
            return

        try:
            import serial

            self._marker_device = serial.Serial(
                port=port_name,
                baudrate=self.settings.marker_baudrate,
                timeout=0.001,
            )

            self.logger.ok(f"Marqueurs série actifs : {port_name}")

        except Exception as exc:
            self.logger.warning(f"Marqueurs série indisponibles : {exc}")
            self._marker_device = None

    def marker(self, code: int) -> None:
        """Envoie un marqueur, sans jamais interrompre la tâche."""
        if self._closed or self._marker_device is None:
            return

        try:
            code = int(code) & 0xFF

            if self.settings.marker_transport.lower() == "parallel":
                self._marker_device.setData(code)
                time.sleep(self.settings.marker_pulse_seconds)
                self._marker_device.setData(0)

            elif self.settings.marker_transport.lower() == "serial":
                self._marker_device.write(bytes([code]))

        except Exception as exc:
            self.logger.warning(f"Erreur marqueur {code}: {exc}")

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    @property
    def audio(self):
        if self._audio is None:
            self._audio = AudioManager(self.settings, self.logger)

        return self._audio

    # ------------------------------------------------------------------
    # EyeLink
    # ------------------------------------------------------------------

    def _init_eyetracker(self) -> None:
        try:
            import pylink

            self._eyetracker = pylink.EyeLink(self.settings.eyetracker_host)
            self.logger.ok("Eye-tracker connecté.")

        except Exception as exc:
            self.logger.warning(f"Eye-tracker indisponible : {exc}")
            self._eyetracker = None

    @property
    def has_eyetracker(self) -> bool:
        return self._eyetracker is not None

    def eyetracker_message(self, message: str) -> None:
        if self._eyetracker is None:
            return

        try:
            self._eyetracker.sendMessage(message)
        except Exception:
            pass

    def eyetracker_start(self, filename: str) -> None:
        if self._eyetracker is None:
            return

        try:
            self._eyetracker.openDataFile(filename)
            self._eyetracker.startRecording(1, 1, 1, 1)
        except Exception as exc:
            self.logger.warning(f"Eye-tracker start impossible : {exc}")

    def eyetracker_stop_and_download(self, output_dir: Path) -> Path | None:
        if self._eyetracker is None:
            return None

        try:
            self._eyetracker.stopRecording()
        except Exception:
            pass

        try:
            self._eyetracker.closeDataFile()
        except Exception:
            pass

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            destination = output_dir / "eyetracker.edf"
            self._eyetracker.receiveDataFile("", str(destination))
            return destination
        except Exception as exc:
            self.logger.warning(f"Téléchargement EDF impossible : {exc}")
            return None

    # ------------------------------------------------------------------
    # Microphone
    # ------------------------------------------------------------------

    def start_microphone(self, output_path: Path, clock) -> bool:
        if not self.settings.microphone_enabled:
            return False

        if self._microphone is None:
            self._microphone = MicrophoneRecorder(
                sample_rate=self.settings.microphone_sample_rate,
                channels=self.settings.microphone_channels,
                logger=self.logger,
            )

        return self._microphone.start(output_path, clock)

    def stop_microphone(self, clock) -> Path | None:
        if self._microphone is None:
            return None

        return self._microphone.stop(clock)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        if self._audio is not None:
            try:
                self._audio.close()
            except Exception:
                pass

        if self._microphone is not None:
            try:
                self._microphone.close()
            except Exception:
                pass

        if self._marker_device is not None:
            try:
                if self.settings.marker_transport.lower() == "parallel":
                    self._marker_device.setData(0)

                if hasattr(self._marker_device, "close"):
                    self._marker_device.close()
            except Exception:
                pass

        if self._trigger_serial is not None:
            try:
                self._trigger_serial.close()
            except Exception:
                pass

        if self._eyetracker is not None:
            try:
                self._eyetracker.close()
            except Exception:
                pass


class AudioManager:
    """Audio préchargé avec scheduling PTB lorsque disponible."""

    _configured = False

    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger
        self.sounds: dict[str, object] = {}

        self._configure_backend()

        from psychopy import sound

        self._sound_class = sound.Sound

    def _configure_backend(self) -> None:
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
        sound = self._sound_class(
            value=frequency,
            secs=duration,
            sampleRate=self.settings.audio_sample_rate,
            stereo=True,
        )
        sound.setVolume(volume)
        self.sounds[name] = sound

    def preload_file(self, name: str, path: Path, volume: float = 1.0) -> None:
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
        self._sound(name).play()

    def play_scheduled(self, name: str, target_time: float, clock) -> float:
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
        try:
            from psychtoolbox import GetSecs

            return GetSecs() + delay

        except Exception:
            return None

    def _sound(self, name: str):
        try:
            return self.sounds[name]
        except KeyError as exc:
            raise KeyError(f"Son non préchargé : '{name}'") from exc

    def close(self) -> None:
        for sound in self.sounds.values():
            try:
                sound.stop()
            except Exception:
                pass

        self.sounds.clear()


class MicrophoneRecorder:
    """Enregistrement WAV continu optionnel via sounddevice."""

    def __init__(self, sample_rate: int, channels: int, logger):
        self.sample_rate = sample_rate
        self.channels = channels
        self.logger = logger

        self._stream = None
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._output_path: Path | None = None

    def start(self, output_path: Path, clock) -> bool:
        if self._recording:
            return False

        try:
            import sounddevice as sd

            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._output_path = output_path
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

    def _callback(self, indata, frames, time_info, status) -> None:
        if self._recording:
            self._frames.append(indata.copy())

    def stop(self, clock=None) -> Path | None:
        if not self._recording:
            return None

        self._recording = False

        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass

        self._stream = None

        if not self._frames or self._output_path is None:
            return None

        try:
            audio = np.concatenate(self._frames, axis=0)

            with wave.open(str(self._output_path), "wb") as wav:
                wav.setnchannels(self.channels)
                wav.setsampwidth(2)
                wav.setframerate(self.sample_rate)
                wav.writeframes(audio.tobytes())

            timestamp = f"{clock.time:.3f}s" if clock is not None else "cleanup"

            self.logger.ok(
                f"Microphone sauvegardé : {self._output_path.name} "
                f"| t={timestamp}"
            )

            self._frames = []
            return self._output_path

        except Exception as exc:
            self.logger.warning(f"Sauvegarde microphone impossible : {exc}")
            return None
        
    def close(self) -> None:
        if self._recording:
            try:
                self.stop(clock=None)
            except Exception:
                pass