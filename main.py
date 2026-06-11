#!/usr/bin/env python3
"""
fMRI Experiment Framework — GUI entry point (PyQt6).

Usage:
    python main.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Windows console setup MUST be first
from utils.console import init_console
init_console()


def start_experiment(settings, task_name, design_id, extra_params=None):
    """Called by the launcher after GUI closes."""
    from core.experiment import Experiment

    exp = Experiment(settings)
    try:
        saved = exp.run_task(
            task_name,
            design_id=design_id,
            **(extra_params or {}),
        )
        if saved:
            print(f"\n[OK] Data saved: {saved}")
    finally:
        exp.cleanup()


def main():
    from gui.launcher import run_launcher
    run_launcher(on_start=start_experiment)


if __name__ == '__main__':
    main()