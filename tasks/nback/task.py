from __future__ import annotations

from typing import Any

from collections import defaultdict

from tasks.base import BaseTask


class Task(BaseTask):
    """Tâche de mémoire de travail alternant blocs 0-back et N-back."""

    NAME = "nback"

    def setup_design(self) -> None:
        """Prépare les alphabets pour la génération sans matériel."""
        self.consonants = list(self.config["consonants"])
        self.zero_targets = list(self.config["zero_back_targets"])

    def setup(self) -> None:
        """Crée le stimulus lettre et prépare les réponses cibles."""
        from psychopy import visual

        self.letter = visual.TextStim(
            self.win,
            text="",
            color="white",
            height=0.15,
            bold=True,
        )

        self.go_key = self.settings.responses.get("go", "space")
        self.valid_keys = [self.go_key]

        self.markers = self.config.get("markers", {})

    def instructions(self) -> str:
        """Retourne les consignes générales de la tâche."""
        return (
            "N-BACK\n\n"
            f"0-back : appuyez sur [{self.go_key}] "
            "si la lettre est la cible.\n\n"
            f"2-back : appuyez sur [{self.go_key}] "
            "si la lettre est identique à celle d'il y a deux essais.\n\n"
            "Sinon : ne faites rien.\n\n"
            "Attendez l'autorisation de l'expérimentateur."
        )

    def block_instruction(self, block_index: int, block: dict) -> str:
        """Retourne la consigne du niveau courant et sa cible 0-back."""
        level = int(block["level"])

        if level == 0:
            target = block.get("_target") or self.rng.choice(self.zero_targets)
            block["_target"] = target

            return (
                "0-BACK\n\n"
                f"Appuyez sur [{self.go_key}]\n"
                f"quand vous voyez la lettre :\n\n"
                f"{target}"
            )

        return (
            f"{level}-BACK\n\n"
            f"Appuyez sur [{self.go_key}]\n"
            f"si la lettre est identique à celle\n"
            f"d'il y a {level} essais."
        )

    def build_trials(self, block: dict) -> list[dict]:
        """Construit tous les essais d’un bloc avant le trigger scanner."""
        level = int(block["level"])
        n = int(block["n_trials"])
        n_targets = max(1, round(n * float(self.design.get("target_ratio", 0.3))))

        if level == 0:
            target = block.get("_target") or self.rng.choice(self.zero_targets)
            block["_target"] = target
            return self.build_zero_back(n, n_targets, target)

        return self.build_n_back(level, n, n_targets)

    def build_zero_back(self, n: int, n_targets: int, target: str) -> list[dict]:
        """Construit un bloc 0-back avec un nombre contrôlé de cibles."""
        target_positions = set(self.rng.sample(range(n), min(n_targets, n)))
        trials: list[dict] = []
        previous = None

        for index in range(n):
            if index in target_positions:
                letter = target
                is_target = True
            else:
                available = [
                    char
                    for char in self.consonants
                    if char != target and char != previous
                ] or [char for char in self.consonants if char != target]

                letter = self.rng.choice(available)
                is_target = False

            trials.append({
                "letter": letter,
                "is_target": is_target,
                "trial_type": "target" if is_target else "nontarget",
                "zero_back_target": target,
            })
            previous = letter

        return trials

    def build_n_back(self, level: int, n: int, n_targets: int) -> list[dict]:
        """Construit un bloc N-back en imposant les positions cibles."""
        target_positions = set(
            self.rng.sample(
                list(range(level, n)),
                min(n_targets, max(0, n - level)),
            )
        )

        letters: list[str] = []
        trials: list[dict] = []

        for index in range(n):
            if index in target_positions:
                letter = letters[index - level]
                is_target = True
            else:
                forbidden = set()

                if index >= level:
                    forbidden.add(letters[index - level])

                if letters:
                    forbidden.add(letters[-1])

                available = [
                    char for char in self.consonants if char not in forbidden
                ] or self.consonants

                letter = self.rng.choice(available)
                is_target = False

            letters.append(letter)
            trials.append({
                "letter": letter,
                "is_target": is_target,
                "trial_type": "target" if is_target else "nontarget",
            })

        return trials

    def run_trial(
        self,
        trial: dict[str, Any],
        block_index: int,
        trial_index: int,
        block: dict[str, Any],
    ) -> dict[str, Any]:
        """Présente une lettre et classe hit, miss, fausse alarme ou rejet correct."""
        level = int(block["level"])
        letter = trial["letter"]
        is_target = bool(trial["is_target"])

        self.flush_keyboard()
        self.letter.text = letter

        self.letter.draw()
        self.win.flip()
        onset = self.clock.time

        self.hardware.marker(
            self.markers.get("target" if is_target else "nontarget", 0)
        )

        responded = False
        rt = None

        response_deadline = onset + (
            float(self.design["stim_duration"])
            + float(self.design["isi_duration"])
        )

        stim_deadline = onset + float(self.design["stim_duration"])

        while self.clock.time < response_deadline:
            if not responded:
                keys = self.get_keys(self.valid_keys)

                if keys:
                    responded = True
                    rt = self.clock.time - onset

            if self.clock.time < stim_deadline:
                self.letter.draw()
            else:
                self.fixation.draw()

            self.win.flip()

        hit = int(is_target and responded)
        miss = int(is_target and not responded)
        false_alarm = int(not is_target and responded)
        correct_rejection = int(not is_target and not responded)
        correct = int(hit or correct_rejection)

        if responded:
            self.hardware.marker(
                self.markers.get("hit" if is_target else "false_alarm", 0)
            )

        return self.record(
            block_index=block_index,
            trial_index=trial_index,
            block=block,
            onset=onset,
            duration=float(self.design["stim_duration"]),
            trial_type="target" if is_target else "nontarget",
            n_level=level,
            letter=letter,
            zero_back_target=block.get("_target", ""),
            is_target=int(is_target),
            responded=int(responded),
            rt=round(rt, 4) if rt is not None else None,
            hit=hit,
            miss=miss,
            false_alarm=false_alarm,
            correct_rejection=correct_rejection,
            is_correct=correct,
            isi_duration=float(self.design["isi_duration"]),
        )

    def print_summary(self) -> None:
        """Affiche l’exactitude globale puis par niveau N-back."""
        records = self.writer.records

        if not records:
            return

        total = len(records)
        correct = sum(record["is_correct"] for record in records)

        print(
            f"\nN-BACK : {correct}/{total} corrects "
            f"({100 * correct / total:.1f}%)"
        )

        by_level = defaultdict(list)

        for record in records:
            by_level[record["n_level"]].append(record)

        for level, subset in sorted(by_level.items()):
            accuracy = 100 * sum(x["is_correct"] for x in subset) / len(subset)
            print(f"  {level}-back : {accuracy:.1f}% ({len(subset)} essais)")
