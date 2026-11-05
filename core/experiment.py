"""Orchestration d'un run expérimental PsychoPy."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Type

from core.clock import ExperimentClock
from core.config import SessionSettings
from core.data import DataWriter, OutputPaths
from core.logging import ExperimentLogger
from core.provenance import session_metadata
from hardware import HardwareManager
from hardware.screen import create_psychopy_window


class Experiment:
    """Crée les ressources partagées puis exécute une tâche.

    La classe est intentionnellement courte : elle ne contient aucune logique
    spécifique à Stroop/N-Back/etc. Son rôle est uniquement de fournir fenêtre,
    horloge, hardware, chemins et logger au ``BaseTask``.
    """

    def __init__(self, settings: SessionSettings) -> None:
        """Initialise chemins, logger, horloge, fenêtre et hardware du run."""
        self.settings = settings
        settings.validate()
        self.logger = self.win = self.hardware = None
        self._closed = False
        self.paths = OutputPaths(settings)
        self.paths.ensure()
        try:
            self.logger = ExperimentLogger(self.paths.log_dir)
            self.metadata = session_metadata(settings)
            self.clock = ExperimentClock()
            self.win = create_psychopy_window(settings)
            self.metadata["measured_refresh_rate"] = self.win.measured_refresh_rate
            self.hardware = HardwareManager(settings, self.clock, self.logger)
        except BaseException:
            self.close()
            raise
        self.logger.info(
            "Session initialisée | "
            f"sub={settings.participant} | ses={settings.session} | "
            f"mock={settings.mock_mode}"
        )

    def run(
        self,
        *,
        task_name: str,
        design_id: int,
        task_config: dict[str, Any],
        task_class: Type,
        seed: int | None = None,
    ) -> Path | None:
        """Instancie la tâche et exécute un run complet."""
        run = self.paths.resolve_run(task_name)
        stem = self.paths.stem(task_name, run)
        writer = DataWriter(
            output_dir=self.paths.func_dir,
            stem=stem,
            logger=self.logger,
            enabled=self.settings.save_data,
        )
        try:
            task = task_class(
            win=self.win,
            clock=self.clock,
            settings=self.settings,
            hardware=self.hardware,
            writer=writer,
            logger=self.logger,
            task_name=task_name,
            task_config=copy.deepcopy(task_config),
            design_id=design_id,
            run=run,
            seed=seed,
            session_metadata=self.metadata,
            )
            return task.run()
        finally:
            writer.close()

    def close(self) -> None:
        """Ferme hardware, fenêtre PsychoPy et logger de manière idempotente."""
        if self._closed:
            return
        self._closed = True
        try:
            if self.hardware is not None:
                self.hardware.close()
        finally:
            try:
                if self.win is not None:
                    self.win.close()
            except Exception:
                pass
            if self.logger is not None:
                self.logger.close()

    def __enter__(self) -> "Experiment":
        """Permet ``with Experiment(settings) as experiment``."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> None:
        """Garantit le cleanup à la sortie d'un context manager."""
        del exc_type, exc, traceback
        self.close()
