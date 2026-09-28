import random

from tasks import load_task_config
from tasks.stroop.sequence import (
    build_condition_trials,
    build_event_trials,
    max_run,
    order_trials,
    validate_sequence,
)


def build_design(design_id: int, seed: int):
    config = load_task_config("stroop")
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


def test_stroop_sequences_validate():
    config = load_task_config("stroop")

    for design_id, design in config["designs"].items():
        for seed in range(20):
            blocks = build_design(design_id, seed)

            validate_sequence(
                blocks,
                event_related=design.get("paradigm") == "event",
            )


def test_event_design_alternates_trial_types():
    blocks = build_design(4, 42)
    trial_types = [trial["trial_type"] for trial in blocks[0]]

    assert max_run(trial_types) == 1


def test_same_seed_produces_same_sequence():
    assert build_design(1, 12345) == build_design(1, 12345)