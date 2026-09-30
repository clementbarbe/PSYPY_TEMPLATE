"""Émulateurs hardware pour développement sans scanner ni périphériques."""

from __future__ import annotations

from typing import Any
from pathlib import Path


class MockTriggerReceiver:
    """Simule un trigger immédiatement afin de ne jamais bloquer un test local."""

    def __init__(self, logger: Any) -> None:
        """Conserve le logger utilisé pour tracer la simulation."""
        self.logger = logger

    def wait(self, response_box: Any, quit_key: str) -> bool:
        """Retourne immédiatement ``True`` et journalise la simulation."""
        del response_box, quit_key
        self.logger.info("[MOCK] Trigger scanner simulé.")
        return True

    def close(self) -> None:
        """Ne fait rien."""


class MockMarkerOutput:
    """Journalise les marqueurs au lieu de piloter une interface TTL."""

    def __init__(self, logger: Any) -> None:
        """Conserve le logger utilisé pour tracer les marqueurs mock."""
        self.logger = logger

    def send(self, code: int) -> None:
        """Journalise un code simulé non nul."""
        if int(code):
            self.logger.info(f"[MOCK] Marker {int(code) & 0xFF}")

    def close(self) -> None:
        """Ne fait rien."""


class MockEyeTracker:
    """Simule les appels d'un eye-tracker sans produire de fichier EDF."""

    connected = True

    def __init__(self, logger: Any) -> None:
        """Conserve le logger utilisé pour tracer l’eye-tracker mock."""
        self.logger = logger

    def message(self, message: str) -> None:
        """Journalise un message eye-tracker simulé."""
        self.logger.info(f"[MOCK ET] {message}")

    def start(self, filename: str) -> None:
        """Journalise le début d'un enregistrement simulé."""
        self.logger.info(f"[MOCK ET] Start {filename}")

    def stop_and_download(self, output_dir: Path) -> Path | None:
        """Journalise l'arrêt sans créer de faux fichier de données."""
        self.logger.info(f"[MOCK ET] Stop ({output_dir})")
        return None

    def close(self) -> None:
        """Ne fait rien."""
