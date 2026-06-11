#!/usr/bin/env python3
"""
fMRI Experiment Framework — CLI entry point.

Usage:
    python run_experiment.py --pid 01 --task flanker --design 1
    python run_experiment.py --pid 01 --task nback --design 3 --scanner cima --mode fmri
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.console import init_console
init_console()


def parse_args():
    p = argparse.ArgumentParser(description='fMRI Experiment Framework')
    p.add_argument('--pid', required=True, help='Participant ID')
    p.add_argument('--session', default='01', help='Session (default: 01)')
    p.add_argument('--task', required=True, help='Task name (flanker, nback)')
    p.add_argument('--design', type=int, default=1, help='Design ID (default: 1)')
    p.add_argument('--scanner', default='pc', help='Scanner (default: pc)')
    p.add_argument('--mode', default='pc', choices=['pc', 'fmri'])
    p.add_argument('--no-fullscreen', action='store_true')
    p.add_argument('--no-triggers', action='store_true')
    return p.parse_args()


def main():
    args = parse_args()

    from config.settings import ExperimentSettings
    from core.experiment import Experiment

    settings = ExperimentSettings(
        participant_id=args.pid,
        session=args.session,
        scanner_name=args.scanner,
        mode=args.mode,
        fullscreen=(not args.no_fullscreen and args.mode == 'fmri'),
        trigger_output_enabled=(not args.no_triggers),
    )

    exp = Experiment(settings)
    try:
        saved = exp.run_task(args.task, design_id=args.design)
        if saved:
            print(f"\n[OK] Data saved: {saved}")
    finally:
        exp.cleanup()


if __name__ == '__main__':
    main()