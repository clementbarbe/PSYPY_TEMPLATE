from __future__ import annotations

from typing import Any

from core.design import DesignGenerator
from tasks.base import BaseTask


class Task(BaseTask):
    """Tâche Eriksen Flanker visuelle."""

    NAME = "flanker"

    def setup(self) -> None:
        """Crée le stimulus de flèches et prépare le mapping des réponses."""
        from psychopy import visual

        self.arrow = visual.TextStim(
            self.win,
            text="",
            color="white",
            height=0.15,
            bold=True,
            font="monospace",
        )

        self.left_key = self.settings.responses.get("left", "left")
        self.right_key = self.settings.responses.get("right", "right")

        self.valid_keys = [self.left_key, self.right_key]
        self.key_to_direction = {
            self.left_key: "left",
            self.right_key: "right",
        }

        self.markers = self.config.get("markers", {})

    def instructions(self) -> str:
        """Retourne les consignes générales du Flanker."""
        return (
            "FLANKER\n\n"
            "Répondez à la direction de la flèche CENTRALE.\n"
            "Ignorez les flèches autour.\n\n"
            f"Gauche : [{self.left_key}]\n"
            f"Droite : [{self.right_key}]\n\n"
            "Répondez vite et précisément.\n\n"
            "Attendez l'autorisation de l'expérimentateur."
        )

    def block_instruction(self, block_index: int, block: dict) -> str | None:
        """Retourne le rappel de consigne affiché avant un bloc."""
        return (
            f"Bloc {block_index + 1}/{len(self.blocks)}\n\n"
            "Répondez à la flèche centrale."
        )

    def build_trials(self, block: dict) -> list[dict]:
        """Construit un bloc équilibré puis applique la pseudo-randomisation."""
        condition = block["condition"]
        n_trials = int(block["n_trials"])
        trials: list[dict] = []

        if condition == "congruent":
            trials = [
                {"target": "left", "flankers": "left", "condition": "congruent"},
                {"target": "right", "flankers": "right", "condition": "congruent"},
            ] * (n_trials // 2)

        elif condition == "incongruent":
            trials = [
                {"target": "left", "flankers": "right", "condition": "incongruent"},
                {"target": "right", "flankers": "left", "condition": "incongruent"},
            ] * (n_trials // 2)

        elif condition == "neutral":
            trials = [
                {"target": "left", "flankers": "neutral", "condition": "neutral"},
                {"target": "right", "flankers": "neutral", "condition": "neutral"},
            ] * (n_trials // 2)

        elif condition == "mixed":
            n_incongruent = round(
                n_trials * float(block.get("prop_incongruent", 0.5))
            )
            n_congruent = n_trials - n_incongruent

            trials = (
                [
                    {
                        "target": "left",
                        "flankers": "left",
                        "condition": "congruent",
                    },
                    {
                        "target": "right",
                        "flankers": "right",
                        "condition": "congruent",
                    },
                ]
                * (n_congruent // 2)
                + [
                    {
                        "target": "left",
                        "flankers": "right",
                        "condition": "incongruent",
                    },
                    {
                        "target": "right",
                        "flankers": "left",
                        "condition": "incongruent",
                    },
                ]
                * (n_incongruent // 2)
            )

        else:
            raise ValueError(f"Condition Flanker inconnue : {condition}")

        while len(trials) < n_trials:
            trials.append(
                {
                    "target": self.rng.choice(["left", "right"]),
                    "flankers": "neutral",
                    "condition": "neutral",
                }
            )

        if condition == "mixed":
            trials = DesignGenerator.shuffle_constrained(
                trials,
                rng=self.rng,
                key=lambda trial: trial["condition"],
                max_consecutive=int(self.design.get("max_consecutive_condition", 3)),
            )
        else:
            self.rng.shuffle(trials)

        for trial in trials:
            trial["isi"] = round(
                self.rng.uniform(
                    float(self.design.get("isi_min", 1.0)),
                    float(self.design.get("isi_max", 1.0)),
                ),
                4,
            )

        return trials

    def run_trial(
        self,
        trial: dict[str, Any],
        block_index: int,
        trial_index: int,
        block: dict[str, Any],
    ) -> dict[str, Any]:
        """Présente un essai Flanker et calcule exactitude et temps de réponse."""
        target = trial["target"]
        flankers = trial["flankers"]
        condition = trial["condition"]

        self.arrow.text = self.make_arrows(target, flankers)
        self.flush_keyboard()

        self.arrow.draw()
        self.win.flip()
        onset = self.clock.time

        marker = self.markers.get(condition, 0)

        if marker:
            self.hardware.marker(marker)

        responded = False
        response = None
        rt = None

        deadline = onset + float(self.design["stim_duration"])

        while self.clock.time < deadline:
            if not responded:
                keys = self.get_keys(self.valid_keys)

                if keys:
                    response = keys[0].name
                    rt = self.clock.time - onset
                    responded = True

            self.arrow.draw()
            self.win.flip()

        isi_deadline = self.clock.time + trial["isi"]

        while self.clock.time < isi_deadline:
            if not responded:
                keys = self.get_keys(self.valid_keys)

                if keys:
                    response = keys[0].name
                    rt = self.clock.time - onset
                    responded = True

            self.fixation.draw()
            self.win.flip()

        response_direction = self.key_to_direction.get(response)
        correct = response_direction == target

        self.hardware.marker(
            self.markers.get("correct" if correct else "incorrect", 0)
        )

        return self.record(
            block_index=block_index,
            trial_index=trial_index,
            block=block,
            onset=onset,
            duration=float(self.design["stim_duration"]),
            trial_type=condition,
            target_direction=target,
            flanker_direction=flankers,
            stimulus=self.arrow.text,
            response_key=response,
            response_direction=response_direction,
            correct_key=(
                self.left_key if target == "left" else self.right_key
            ),
            rt=round(rt, 4) if rt is not None else None,
            responded=int(responded),
            is_correct=int(correct),
            is_error=int(responded and not correct),
            is_miss=int(not responded),
            isi=trial["isi"],
        )

    @staticmethod
    def make_arrows(target: str, flankers: str) -> str:
        """Retourne la chaîne de cinq symboles correspondant à un essai."""
        center = "<" if target == "left" else ">"

        if flankers == "neutral":
            side = "-"

        else:
            side = "<" if flankers == "left" else ">"

        return f"{side} {side} {center} {side} {side}"