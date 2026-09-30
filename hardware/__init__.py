"""Façade hardware à plat utilisée par les tâches."""

from __future__ import annotations

from typing import Any
from pathlib import Path

from hardware.audio import AudioManager
from hardware.eyetracker import NullEyeTracker, create_eyetracker
from hardware.microphone import MicrophoneRecorder
from hardware.mock import MockEyeTracker, MockMarkerOutput, MockTriggerReceiver
from hardware.response_box import create_response_box
from hardware.triggers import MarkerOutput, TriggerReceiver


class HardwareManager:
    """Regroupe les périphériques derrière une API stable pour les tâches."""

    def __init__(self, settings: Any, clock: Any, logger: Any) -> None:
        """Construit les périphériques réels ou simulés de la session."""
        self.settings = settings
        self.clock = clock
        self.logger = logger
        self.response_box = create_response_box(settings, clock, logger)
        if settings.mock_mode:
            self.trigger = (
                MockTriggerReceiver(logger)
                if settings.trigger_enabled
                else TriggerReceiver(settings, logger)
            )
            self.markers = (
                MockMarkerOutput(logger)
                if settings.markers_enabled
                else MarkerOutput(settings, logger)
            )
            self.eyetracker = (
                MockEyeTracker(logger)
                if settings.eyetracker_enabled
                else NullEyeTracker()
            )
        else:
            self.trigger = TriggerReceiver(settings, logger)
            self.markers = MarkerOutput(settings, logger)
            try:
                self.eyetracker = create_eyetracker(settings, logger)
            except Exception as exc:
                logger.warning(f"Eye-tracker indisponible : {exc}")
                self.eyetracker = NullEyeTracker()
        self._audio: AudioManager | None = None
        self._microphone: MicrophoneRecorder | None = None
        self._closed = False

    @property
    def audio(self) -> AudioManager:
        """Construit paresseusement le gestionnaire audio."""
        if self._audio is None:
            self._audio = AudioManager(self.settings, self.logger)
        return self._audio

    def wait_for_trigger(self) -> bool:
        """Attend le trigger scanner via le backend configuré."""
        return self.trigger.wait(self.response_box, self.settings.quit_key)

    def marker(self, code: int) -> None:
        """Envoie un marqueur si son code est non nul."""
        if int(code):
            self.markers.send(int(code))

    @property
    def has_eyetracker(self) -> bool:
        """Indique si un backend eye-tracker actif est disponible."""
        return bool(getattr(self.eyetracker, "connected", False))

    def eyetracker_message(self, message: str) -> None:
        """Envoie un message temporel au backend eye-tracker."""
        try:
            self.eyetracker.message(message)
        except Exception as exc:
            self.logger.warning(f"Message eye-tracker impossible : {exc}")

    def eyetracker_start(self, filename: str) -> None:
        """Démarre l'enregistrement eye-tracker."""
        try:
            self.eyetracker.start(filename)
        except Exception as exc:
            self.logger.warning(f"Démarrage eye-tracker impossible : {exc}")

    def eyetracker_stop_and_download(self, output_dir: Path) -> Path | None:
        """Arrête le tracker et récupère ses données locales si nécessaire."""
        try:
            return self.eyetracker.stop_and_download(Path(output_dir))
        except Exception as exc:
            self.logger.warning(f"Arrêt/téléchargement eye-tracker impossible : {exc}")
            return None

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
        return self._microphone.start(Path(output_path), self.clock)

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
        for device in (self._audio, self._microphone, self.markers, self.trigger, self.response_box, self.eyetracker):
            if device is None:
                continue
            try:
                device.close()
            except Exception:
                pass


__all__ = ["HardwareManager"]
