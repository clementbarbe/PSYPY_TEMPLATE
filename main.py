#!/usr/bin/env python3
"""
fMRI Experiment Framework — entry point.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.console import init_console
init_console()


def main():
    from gui.launcher import show_menu

    config = show_menu()
    if config is None:
        print("Ferme sans lancer d'experience.")
        return

    from core.experiment import Experiment

    settings = config['settings']
    task_name = config['task_name']
    design_id = config['design_id']
    extra = config.get('extra_params', {})

    exp = Experiment(settings)
    try:
        saved = exp.run_task(task_name, design_id=design_id, **extra)
        if saved:
            print(f"\n[OK] Data saved: {saved}")
    finally:
        exp.cleanup()


if __name__ == '__main__':
    main()