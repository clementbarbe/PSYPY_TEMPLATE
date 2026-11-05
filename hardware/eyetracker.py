"""Backends EyeLink et Tobii derrière une interface commune très petite."""

from __future__ import annotations

import csv
import base64
import secrets
from pathlib import Path
from typing import Any


class NullEyeTracker:
    """Implémentation inactive utilisée lorsque l'eye-tracker est désactivé."""

    connected = False

    def message(self, message: str) -> None:
        """Ignore un message expérimental."""
        del message

    def start(self, filename: str) -> None:
        """Ignore le démarrage d'enregistrement."""
        del filename

    def stop_and_download(self, output_dir: Path) -> Path | None:
        """Retourne ``None`` car aucune donnée n'a été acquise."""
        del output_dir
        return None

    def close(self) -> None:
        """Ne fait rien."""


class EyeLinkTracker:
    """Backend SR Research EyeLink via ``pylink``."""

    _allocated_names: set[str] = set()

    def __init__(self, host: str, logger: Any) -> None:
        """Établit la connexion EyeLink au host configuré."""
        import pylink

        self.logger = logger
        self._pylink = pylink
        self._tracker = pylink.EyeLink(host)
        self._remote_filename: str | None = None
        self._local_stem: str | None = None
        self._recording = False
        self.connected = True

    def message(self, message: str) -> None:
        """Envoie un message temporel au fichier EDF."""
        self._tracker.sendMessage(str(message))

    def start(self, filename: str) -> None:
        """Ouvre un EDF et démarre l'enregistrement EyeLink."""
        # EyeLink impose un nom DOS court ; le stem BIDS complet reste côté PC.
        self._local_stem = Path(filename).stem
        self._remote_filename = self._new_remote_filename()
        self.logger.info(f"EDF : {self._remote_filename} <-> {self._local_stem}")
        self._tracker.openDataFile(self._remote_filename)
        result = self._tracker.startRecording(1, 1, 1, 1)
        if result not in (None, 0):
            raise RuntimeError(f"EyeLink startRecording a échoué : {result}")
        self._recording = True

    @classmethod
    def _new_remote_filename(cls) -> str:
        """Alloue huit caractères alphanumériques indépendants du préfixe BIDS."""
        while True:
            name = base64.b32encode(secrets.token_bytes(5)).decode("ascii") + ".EDF"
            if name not in cls._allocated_names:
                cls._allocated_names.add(name)
                return name

    @property
    def remote_filename(self) -> str | None:
        """Expose la correspondance EDF à sauvegarder avec le run."""
        return self._remote_filename

    def stop_and_download(self, output_dir: Path) -> Path | None:
        """Arrête l'EyeLink et récupère l'EDF dans le dossier fonctionnel."""
        if self._remote_filename is None:
            return None
        if self._recording:
            self._tracker.stopRecording()
            self._recording = False
        self._tracker.setOfflineMode()
        self._tracker.closeDataFile()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        local_stem = self._local_stem or "eyetracker"
        destination = output_dir / f"{local_stem}_eyetrack.edf"
        if destination.exists():
            raise FileExistsError(f"EDF local déjà présent : {destination}")
        self._tracker.receiveDataFile(self._remote_filename, str(destination))
        if not destination.exists() or destination.stat().st_size == 0:
            raise OSError(f"EDF non récupéré : {self._remote_filename}")
        self._remote_filename = None
        return destination

    def close(self) -> None:
        """Ferme la connexion EyeLink."""
        try:
            if self._recording:
                self._tracker.stopRecording()
                self._recording = False
            if self._remote_filename is not None:
                self._tracker.setOfflineMode()
                self._tracker.closeDataFile()
        finally:
            self._tracker.close()


class TobiiTracker:
    """Backend Tobii Pro qui sauvegarde les échantillons de regard en TSV."""

    def __init__(self, logger: Any) -> None:
        """Sélectionne le premier Tobii Pro disponible via le SDK."""
        import tobii_research as tr

        trackers = tr.find_all_eyetrackers()
        if not trackers:
            raise RuntimeError("Aucun eye-tracker Tobii détecté.")
        self.logger = logger
        self._tr = tr
        self._tracker = trackers[0]
        self._samples: list[dict[str, Any]] = []
        self._messages: list[dict[str, Any]] = []
        self._recording = False
        self._filename = "eyetracker"
        self.connected = True

    def _gaze_callback(self, sample: dict[str, Any]) -> None:
        """Collecte un échantillon fourni par le SDK Tobii."""
        if self._recording:
            self._samples.append(dict(sample))

    def message(self, message: str) -> None:
        """Conserve un message logiciel pour le fichier annexe Tobii."""
        self._messages.append({"message": str(message), "sample_index": len(self._samples)})

    def start(self, filename: str) -> None:
        """Démarre la souscription aux données de regard."""
        self._filename = Path(filename).stem
        self._samples = []
        self._messages = []
        self._recording = True
        self._tracker.subscribe_to(
            self._tr.EYETRACKER_GAZE_DATA,
            self._gaze_callback,
            as_dictionary=True,
        )

    def stop_and_download(self, output_dir: Path) -> Path | None:
        """Arrête la souscription et écrit les échantillons Tobii en TSV."""
        if not self._recording:
            return None
        self._recording = False
        self._tracker.unsubscribe_from(self._tr.EYETRACKER_GAZE_DATA, self._gaze_callback)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        destination = output_dir / f"{self._filename}_eyetrack.tsv"
        columns: list[str] = []
        for sample in self._samples:
            for key in sample:
                if key not in columns:
                    columns.append(key)
        with destination.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t")
            writer.writeheader()
            writer.writerows(self._samples)
        return destination

    def close(self) -> None:
        """Arrête une souscription encore active."""
        if self._recording:
            try:
                self._tracker.unsubscribe_from(self._tr.EYETRACKER_GAZE_DATA, self._gaze_callback)
            except Exception:
                pass
            self._recording = False


def create_eyetracker(settings: Any, logger: Any) -> Any:
    """Construit le backend configuré ou un tracker nul."""
    if not settings.eyetracker_enabled:
        return NullEyeTracker()
    backend = settings.eyetracker_backend.lower()
    if backend == "eyelink":
        return EyeLinkTracker(settings.eyetracker_host, logger)
    if backend == "tobii":
        return TobiiTracker(logger)
    raise ValueError(f"Backend eye-tracker inconnu : {backend}")

