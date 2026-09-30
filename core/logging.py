"""Journalisation console + fichier, pensée pour l'expérimentateur."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any


class ExperimentLogger:
    """Petit adaptateur autour du module standard : console et fichier.

    Le format reste volontairement compact pendant l'acquisition afin que
    l'expérimentateur puisse repérer instantanément bloc, condition et réponse.
    """

    def __init__(self, log_dir: Path) -> None:
        """Crée les handlers console et fichier pour une session."""
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = log_dir / f"experiment_{stamp}.log"
        self._logger = logging.getLogger(f"fmri.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)-7s] %(message)s", datefmt="%H:%M:%S")
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        file_handler = logging.FileHandler(self.path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self._logger.handlers[:] = [stream, file_handler]
        self._closed = False

    def info(self, message: str) -> None:
        """Écrit une information générale."""
        self._logger.info(message)

    def ok(self, message: str) -> None:
        """Écrit une information de succès sans niveau custom inutile."""
        self._logger.info("OK | %s", message)

    def warning(self, message: str) -> None:
        """Écrit un avertissement non bloquant."""
        self._logger.warning(message)

    def error(self, message: str) -> None:
        """Écrit une erreur."""
        self._logger.error(message)

    def trial(
        self,
        record: dict[str, Any],
        *,
        trial_number: int,
        total_trials: int,
        block_number: int,
        total_blocks: int,
    ) -> None:
        """Affiche une ligne de suivi normalisée après chaque essai."""
        condition = record.get("trial_type", "n/a")
        onset = record.get("onset")
        response = record.get("response_key") or record.get("response") or "-"
        correct = record.get("is_correct")
        rt = record.get("rt")

        if correct is None:
            accuracy = "-"
        else:
            accuracy = "Correct" if bool(correct) else "Incorrect"

        rt_text = f"{float(rt) * 1000:.0f} ms" if rt not in (None, "", "n/a") else "-"
        onset_text = f"{float(onset):.3f}s" if onset is not None else "-"

        self.info(
            f"[Trial {trial_number}/{total_trials} | Bloc {block_number}/{total_blocks}] "
            f"Condition: {condition} | Onset: {onset_text} | "
            f"Réponse: {response} ({accuracy}, RT: {rt_text})"
        )

    def close(self) -> None:
        """Flush et ferme les handlers du logger."""
        if self._closed:
            return
        self._closed = True
        for handler in list(self._logger.handlers):
            try:
                handler.flush()
                handler.close()
            finally:
                self._logger.removeHandler(handler)
