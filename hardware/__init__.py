"""Façade hardware à plat utilisée par les tâches."""

from __future__ import annotations

from typing import Any
from pathlib import Path

from hardware.audio import AudioManager
from hardware.eyetracker import NullEyeTracker, create_eyetracker
from hardware.microphone import MicrophoneRecorder
from hardware.mock import MockEyeTracker, MockMarkerOutput, MockTriggerReceiver
from hardware.response_box import KeyboardResponseBox, create_response_box
from hardware.triggers import MarkerOutput, TriggerReceiver


class HardwareManager:
    """Regroupe les périphériques derrière une API stable pour les tâches."""

    def __init__(self, settings: Any, clock: Any, logger: Any) -> None:
        """Construit les périphériques réels ou simulés de la session."""
        self.settings = settings
        self.clock = clock
        self.logger = logger
        self.response_box = self.keyboard = self.trigger = self.markers = self.eyetracker = None
        self._audio: AudioManager | None = None
        self._microphone: MicrophoneRecorder | None = None
        self.marker_events: list[dict[str, Any]] = []
        self._eyetracker_started = False
        self._closed = False
        try:
            self.response_box = create_response_box(settings, clock, logger)
            self.keyboard = self.response_box if settings.response_box_backend == "keyboard" else KeyboardResponseBox(clock.psychopy_clock)
            self.trigger = MockTriggerReceiver(logger) if settings.mock_mode else TriggerReceiver(settings, logger, clock)
            self.markers = MockMarkerOutput(logger) if settings.mock_mode and settings.markers_enabled else MarkerOutput(settings, logger)
            self.eyetracker = MockEyeTracker(logger) if settings.mock_mode and settings.eyetracker_enabled else create_eyetracker(settings, logger)
        except BaseException:
            self.close()
            raise

    def get_keys(self, key_list: list[str] | None = None) -> list[Any]:
        """Lit les réponses et surveille aussi Escape sur le clavier opérateur."""
        keys = self.response_box.get_keys(key_list, wait_release=False)
        if self.keyboard is not self.response_box:
            keys += self.keyboard.get_keys([self.settings.quit_key], wait_release=False)
        return keys

    @property
    def audio(self) -> AudioManager:
        """Construit paresseusement le gestionnaire audio."""
        if self._audio is None:
            self._audio = AudioManager(self.settings, self.logger)
        return self._audio

    def wait_for_trigger(self) -> bool:
        """Attend le trigger scanner via le backend configuré."""
        return self.trigger.wait(self.keyboard, self.settings.quit_key)

    def marker(self, code: int) -> None:
        """Envoie un marqueur si son code est non nul."""
        if int(code):
            onset = self.clock.time
            self.markers.send(int(code))
            if self.settings.markers_enabled:
                self.marker_events.append({"code": int(code), "onset": onset, "mock": self.settings.mock_mode})

    @property
    def has_eyetracker(self) -> bool:
        """Indique si un backend eye-tracker actif est disponible."""
        return bool(getattr(self.eyetracker, "connected", False))

    def eyetracker_message(self, message: str) -> None:
        """Envoie un message temporel au backend eye-tracker."""
        self.eyetracker.message(message)

    def eyetracker_start(self, filename: str) -> None:
        """Démarre l'enregistrement eye-tracker."""
        self.eyetracker.start(filename)
        self._eyetracker_started = True

    def eyetracker_stop_and_download(self, output_dir: Path) -> Path | None:
        """Arrête le tracker et récupère ses données locales si nécessaire."""
        result = self.eyetracker.stop_and_download(Path(output_dir))
        if self._eyetracker_started and self.settings.eyetracker_enabled and not self.settings.mock_mode and (result is None or not result.exists() or result.stat().st_size == 0):
            raise OSError("Fichier eye-tracker attendu absent ou vide après récupération.")
        return result

    def start_microphone(self, output_path: Path) -> bool:
        """Démarre le microphone optionnel."""
        if not self.settings.microphone_enabled:
            return False
        if self._microphone is None:
            self._microphone = MicrophoneRecorder(
                self.settings.microphone_sample_rate,
                self.settings.microphone_channels,
                self.logger,
            )
        if not self._microphone.start(Path(output_path), self.clock):
            raise RuntimeError("Le microphone demandé n'a pas démarré.")
        return True

    def stop_microphone(self) -> Path | None:
        """Arrête le microphone optionnel."""
        if self._microphone is None:
            return None
        return self._microphone.stop(self.clock)

    def close(self) -> None:
        """Ferme tous les périphériques, même après une exception de tâche."""
        if self._closed:
            return
        self._closed = True
        devices = (self._audio, self._microphone, self.markers, self.trigger, self.response_box, self.eyetracker, self.keyboard)
        seen: set[int] = set()
        for device in devices:
            if device is None:
                continue
            if id(device) in seen:
                continue
            seen.add(id(device))
            try:
                device.close()
            except Exception as exc:
                self.logger.warning(f"Fermeture {type(device).__name__} impossible : {exc}")


__all__ = ["HardwareManager"]
