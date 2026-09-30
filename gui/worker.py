"""Worker QThread qui exécute PsychoPy sans bloquer l'interface Qt."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class ExperimentWorker(QObject):
    """Construit et exécute une expérience dans un thread Qt dédié."""

    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, settings_path: Path, launch_config: dict) -> None:
        """Conserve une copie des paramètres nécessaires au run."""
        super().__init__()
        self.settings_path = Path(settings_path)
        self.launch_config = dict(launch_config)

    @pyqtSlot()
    def run(self) -> None:
        """Exécute le run et émet uniquement des signaux thread-safe vers le GUI."""
        experiment = None
        try:
            from core.config import SessionSettings
            from core.experiment import Experiment
            from tasks import load_task_class, load_task_config

            cfg = self.launch_config
            settings = SessionSettings.from_yaml(
                path=self.settings_path,
                participant=cfg["participant"],
                session=cfg["session"],
                run=cfg.get("run"),
                fullscreen=cfg["fullscreen"],
                screen_index=cfg["screen"],
                wait_for_trigger=cfg["trigger_enabled"],
                markers_enabled=cfg["markers_enabled"],
                eyetracker_enabled=cfg["eyetracker_enabled"],
                mock_mode=cfg["mock_mode"],
                save_data=cfg["save_data"],
            )
            task_name = cfg["task"]
            task_config = load_task_config(task_name)
            task_class = load_task_class(task_name)
            experiment = Experiment(settings)
            saved = experiment.run(
                task_name=task_name,
                design_id=int(cfg["design"]),
                task_config=task_config,
                task_class=task_class,
                seed=cfg.get("seed"),
            )
            self.finished.emit(str(saved) if saved is not None else "")
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            if experiment is not None:
                experiment.close()
