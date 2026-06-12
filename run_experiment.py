#!/usr/bin/env python3
"""
CLI entry point.
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.console import init_console
init_console()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pid', required=True)
    p.add_argument('--session', default='01')
    p.add_argument('--task', required=True)
    p.add_argument('--design', type=int, default=1)
    p.add_argument('--mode', default='pc', choices=['pc', 'fmri'])
    p.add_argument('--screen', type=int, default=0)
    p.add_argument('--no-fullscreen', action='store_true')
    p.add_argument('--no-triggers', action='store_true')
    args = p.parse_args()

    from config.settings import ExperimentSettings
    from core.experiment import Experiment

    settings = ExperimentSettings(
        participant_id=args.pid,
        session=args.session,
        mode=args.mode,
        fullscreen=(not args.no_fullscreen and args.mode == 'fmri'),
        screen_index=args.screen,
        trigger_output_enabled=(not args.no_triggers),
    )

    exp = Experiment(settings)
    try:
        saved = exp.run_task(args.task, design_id=args.design)
        if saved:
            print(f"\n[OK] {saved}")
    finally:
        exp.cleanup()


if __name__ == '__main__':
    main()