"""
Experiment settings — single dataclass for the session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from config.constants import DATA_DIR


@dataclass
class ExperimentSettings:
    """Immutable session-level configuration."""

    participant_id: str
    session: str = '01'
    run: str = '01'

    scanner_name: str = 'pc'
    mode: str = 'pc'              # 'fmri' or 'pc'
    fullscreen: bool = True
    screen_index: int = 0

    eyetracker_enabled: bool = False
    trigger_output_enabled: bool = False
    save_data: bool = True

    data_root: Path = field(default_factory=lambda: DATA_DIR)

    @property
    def subject_dir(self) -> Path:
        return self.data_root / f'sub-{self.participant_id}' / f'ses-{self.session}'

    def task_dir(self, task_name: str) -> Path:
        return self.subject_dir / task_name

    def log_dir(self) -> Path:
        return self.subject_dir / 'logs'

    def output_filename(self, task_name: str, suffix: str = '') -> str:
        base = (
            f"sub-{self.participant_id}_ses-{self.session}"
            f"_task-{task_name}_run-{self.run}"
        )
        if suffix:
            base += f"_{suffix}"
        return base