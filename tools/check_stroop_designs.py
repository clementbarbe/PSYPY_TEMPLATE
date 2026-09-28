#!/usr/bin/env python3
"""
Audit hors PsychoPy des designs Stroop.

Usage :
    python tools/check_stroop_designs.py
    python tools/check_stroop_designs.py --repeats 500
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tasks import load_task_config
from tasks.stroop.sequence import (
    build_condition_trials,
    build_event_trials,
    max_run,
    order_trials,
    validate_sequence,
)


def build(config: dict, design_id: int, seed: int):
    design = config["designs"][design_id]
    rng = random.Random(seed)

    colors = list(config["colors"])
    words = config["color_words"]
    neutral = config["neutral_words"]

    if design.get("paradigm") == "event":
        return [
            build_event_trials(
                count=design["blocks"][0]["n_trials"],
                colors=colors,
                color_words=words,
                neutral_words=neutral,
                rng=rng,
            )
        ]

    blocks = []

    for block in design["blocks"]:
        trials = build_condition_trials(
            condition=block["condition"],
            count=block["n_trials"],
            colors=colors,
            color_words=words,
            neutral_words=neutral,
            rng=rng,
        )

        blocks.append(order_trials(trials, rng))

    return blocks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=100)
    args = parser.parse_args()

    config = load_task_config("stroop")
    all_ok = True

    for design_id in sorted(config["designs"]):
        design = config["designs"][design_id]

        for seed in range(args.repeats):
            blocks = build(config, design_id, seed)

            try:
                validate_sequence(
                    blocks,
                    event_related=design.get("paradigm") == "event",
                )

            except Exception as exc:
                all_ok = False
                print(
                    f"[FAIL] Design {design_id}, seed={seed}: {exc}",
                    file=sys.stderr,
                )
                break

        print(
            f"[{'OK' if all_ok else 'FAIL'}] "
            f"Design {design_id}: {design['name']}"
        )

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())