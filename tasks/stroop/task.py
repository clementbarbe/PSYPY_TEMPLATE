from __future__ import annotations

from collections import defaultdict

from psychopy import visual

from tasks.base import BaseTask
from tasks.stroop.sequence import (
    build_condition_trials,
    build_event_trials,
    order_trials,
    validate_sequence,
)


class Task(BaseTask):
    NAME = "stroop"
    PREGENERATE = True

    def setup(self) -> None:
        cfg = self.config
        display = cfg.get("display", {})

        self.colors = dict(cfg["colors"])
        self.color_words = dict(cfg["color_words"])
        self.color_names = list(self.colors)
        self.neutral_words = list(cfg["neutral_words"])
        self.markers = cfg.get("markers", {})

        self.word_stim = visual.TextStim(
            self.win,
            text="",
            color="white",
            height=float(display.get("word_height", 0.15)),
            bold=True,
            font="monospace",
        )

        self.response_keys = {
            "rouge": self.settings.responses.get("left", "left"),
            "bleu": self.settings.responses.get("down", "down"),
            "vert": self.settings.responses.get("right", "right"),
        }

        self.key_to_color = {
            key: color for color, key in self.response_keys.items()
        }

        self.valid_keys = list(self.key_to_color)

        radius = float(display.get("indicator_radius", 0.028))
        y = float(display.get("indicator_y", -0.82))
        spacing = float(display.get("indicator_spacing", 0.22))

        self.indicators = []

        for index, color_name in enumerate(self.color_names):
            x = spacing * (index - 1)

            self.indicators.append(
                visual.Circle(
                    self.win,
                    radius=radius,
                    pos=(x, y),
                    fillColor=self.colors[color_name],
                    lineColor=self.colors[color_name],
                )
            )

    @classmethod
    def dry_run(cls, task_config: dict, design_id: int, seed=None) -> None:
        super().dry_run(task_config, design_id, seed)

        from random import Random

        design = task_config["designs"][design_id]
        rng = Random(seed)

        colors = list(task_config["colors"])
        words = task_config["color_words"]
        neutrals = task_config["neutral_words"]

        if design.get("paradigm") == "event":
            blocks = [
                build_event_trials(
                    count=design["blocks"][0]["n_trials"],
                    colors=colors,
                    color_words=words,
                    neutral_words=neutrals,
                    rng=rng,
                )
            ]

        else:
            blocks = []

            for block in design["blocks"]:
                trials = build_condition_trials(
                    condition=block["condition"],
                    count=block["n_trials"],
                    colors=colors,
                    color_words=words,
                    neutral_words=neutrals,
                    rng=rng,
                )

                blocks.append(order_trials(trials, rng))

        validate_sequence(
            blocks,
            event_related=design.get("paradigm") == "event",
        )

    def instructions(self) -> str:
        return (
            "STROOP\n\n"
            "Répondez à la COULEUR de l'encre.\n"
            "Ignorez le mot écrit.\n\n"
            f"ROUGE : [{self.response_keys['rouge']}]\n"
            f"BLEU  : [{self.response_keys['bleu']}]\n"
            f"VERT  : [{self.response_keys['vert']}]\n\n"
            "Répondez vite et précisément.\n\n"
            "Appuyez sur une touche pour commencer."
        )

    def build_all_trials(self) -> list[list[dict]]:
        if self.design.get("paradigm") == "event":
            count = int(self.blocks[0]["n_trials"])

            return [
                build_event_trials(
                    count=count,
                    colors=self.color_names,
                    color_words=self.color_words,
                    neutral_words=self.neutral_words,
                    rng=self.rng,
                )
            ]

        blocks = []

        for block in self.blocks:
            trials = build_condition_trials(
                condition=block["condition"],
                count=int(block["n_trials"]),
                colors=self.color_names,
                color_words=self.color_words,
                neutral_words=self.neutral_words,
                rng=self.rng,
            )

            blocks.append(order_trials(trials, rng=self.rng))

        return blocks

    def validate_trials(self, blocks: list[list]) -> None:
        validate_sequence(
            blocks,
            event_related=self.design.get("paradigm") == "event",
        )

    def run_trial(self, trial, block_index, trial_index, block) -> dict:
        word = trial["word"]
        ink = trial["ink"]
        trial_type = trial["trial_type"]

        fixation_duration = float(self.design["fixation_duration"])
        stim_duration = float(self.design["stim_duration"])

        if self.design.get("paradigm") == "event":
            iti = self.rng.uniform(
                float(self.design["iti_min"]),
                float(self.design["iti_max"]),
            )
        else:
            iti = float(self.design["iti_duration"])

        self.flush_keyboard()

        fixation_deadline = self.clock.time + fixation_duration

        while self.clock.time < fixation_deadline:
            self.fixation.draw()
            self.win.flip()
            self.get_keys([])

        self.word_stim.text = word
        self.word_stim.color = self.colors[ink]

        self.word_stim.draw()
        self.win.flip()
        onset = self.clock.time

        self.hardware.marker(self.markers.get(trial_type, 0))

        responded = False
        response_key = None
        response_color = None
        rt = None

        deadline = onset + stim_duration

        while self.clock.time < deadline:
            if not responded:
                keys = self.get_keys(self.valid_keys)

                if keys:
                    response_key = keys[0].name
                    response_color = self.key_to_color.get(response_key)
                    rt = self.clock.time - onset
                    responded = True

            self.word_stim.draw()
            self.win.flip()

        iti_deadline = self.clock.time + iti
        guide_visible = False

        while self.clock.time < iti_deadline:
            if not responded:
                keys = self.get_keys(self.valid_keys)

                if keys:
                    response_key = keys[0].name
                    response_color = self.key_to_color.get(response_key)
                    rt = self.clock.time - onset
                    responded = True

            self.fixation.draw()

            for circle in self.indicators:
                circle.draw()

            guide_visible = True
            self.win.flip()

        correct = response_color == ink

        self.hardware.marker(
            self.markers.get("correct" if correct else "incorrect", 0)
        )

        return self.record(
            block_index=block_index,
            trial_index=trial_index,
            block=block,
            onset=onset,
            duration=stim_duration,
            trial_type=trial_type,
            word=word,
            ink_color=ink,
            correct_color=ink,
            correct_key=self.response_keys[ink],
            response_key=response_key,
            response_color=response_color,
            responded=int(responded),
            rt=round(rt, 4) if rt is not None else None,
            is_correct=int(correct),
            is_error=int(responded and not correct),
            is_miss=int(not responded),
            fixation_duration=fixation_duration,
            iti_duration=round(iti, 4),
            guide_shown=int(guide_visible),
        )

    def print_summary(self) -> None:
        records = self.writer.records

        if not records:
            return

        by_type = defaultdict(list)

        for record in records:
            by_type[record["trial_type"]].append(record)

        print("\nSTROOP")

        for condition, subset in sorted(by_type.items()):
            correct = sum(record["is_correct"] for record in subset)
            accuracy = 100 * correct / len(subset)

            rts = [
                record["rt"]
                for record in subset
                if record["is_correct"] and record["rt"] is not None
            ]

            rt_text = f"{1000 * sum(rts) / len(rts):.0f} ms" if rts else "-"

            print(
                f"  {condition:12} : {accuracy:5.1f}% "
                f"| RT correct = {rt_text}"
            )