"""
Subject / session management utilities.
"""

from __future__ import annotations

from pathlib import Path
from config.settings import ExperimentSettings


def ensure_directories(settings: ExperimentSettings, task_name: str) -> Path:
    """Create subject/session/task directory tree. Return task dir."""
    task_dir = settings.task_dir(task_name)
    task_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir().mkdir(parents=True, exist_ok=True)
    return task_dir


def check_existing_data(settings: ExperimentSettings, task_name: str) -> list[Path]:
    """Return list of existing data files for this subject/session/task."""
    task_dir = settings.task_dir(task_name)
    if not task_dir.exists():
        return []
    return sorted(task_dir.glob('*.csv'))


def next_run_number(settings: ExperimentSettings, task_name: str) -> str:
    """Determine next run number based on existing files."""
    existing = check_existing_data(settings, task_name)
    return f"{len(existing) + 1:02d}"