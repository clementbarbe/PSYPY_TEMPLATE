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

        self.show_indicators = bool(display.get("show_indicators", True))
        self.indicator_hide_lead = float(
            display.get("indicator_hide_lead", 2.0)
        )

        # Heure attendue du prochain stimulus.
        # None signifie qu'aucun stimulus imminent n'est connu.
        self.next_stim_time: float | None = None

        # Les indicateurs sont désactivés pendant le repos final.
        self.guide_enabled = True

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

        if self.show_indicators:
            x_start = -spacing * (len(self.color_names) - 1) / 2.0

            for index, color_name in enumerate(self.color_names):
                self.indicators.append(
                    visual.Circle(
                        self.win,
                        radius=radius,
                        edges=64,
                        pos=(x_start + index * spacing, y),
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
        """
        Génère toute la séquence avant le trigger.

        Chaque essai contient :
            word
            ink
            trial_type
            iti
        """
        if self.design.get("paradigm") == "event":
            count = int(self.blocks[0]["n_trials"])

            trials = build_event_trials(
                count=count,
                colors=self.color_names,
                color_words=self.color_words,
                neutral_words=self.neutral_words,
                rng=self.rng,
            )

            iti_min = float(self.design["iti_min"])
            iti_max = float(self.design["iti_max"])

            # ITI stratifiés : moyenne exacte et couverture de l'intervalle.
            itis = [
                iti_min + (iti_max - iti_min) * (index + 0.5) / count
                for index in range(count)
            ]

            self.rng.shuffle(itis)

            for trial, iti in zip(trials, itis):
                trial["iti"] = round(iti, 4)

            return [trials]

        prepared_blocks: list[list[dict]] = []

        fixed_iti = float(self.design["iti_duration"])

        for block in self.blocks:
            trials = build_condition_trials(
                condition=block["condition"],
                count=int(block["n_trials"]),
                colors=self.color_names,
                color_words=self.color_words,
                neutral_words=self.neutral_words,
                rng=self.rng,
            )

            trials = order_trials(
                trials,
                rng=self.rng,
                max_same_word=2,
                max_same_ink=2,
            )

            for trial in trials:
                trial["iti"] = fixed_iti

            prepared_blocks.append(trials)

        return prepared_blocks

    def validate_trials(self, blocks: list[list]) -> None:
        validate_sequence(
            blocks,
            event_related=self.design.get("paradigm") == "event",
        )

    # ------------------------------------------------------------------
    # Guide couleurs
    # ------------------------------------------------------------------

    def guide_visible(self) -> bool:
        """
        Le guide est affiché uniquement :
        - pendant les ITI ;
        - pendant les repos inter-blocs ;
        - jamais pendant fixation pré-stimulus ;
        - jamais pendant stimulus ;
        - jamais dans les deux secondes précédant un stimulus.
        """
        if not self.guide_enabled:
            return False

        if not self.indicators:
            return False

        # Aucun prochain stimulus prévu : le guide peut être visible.
        if self.next_stim_time is None:
            return True

        remaining = self.next_stim_time - self.clock.time

        return remaining > self.indicator_hide_lead

    def draw_guide(self) -> bool:
        """
        Dessine le guide si autorisé.

        Retourne True si le guide était effectivement visible.
        """
        if not self.guide_visible():
            return False

        for indicator in self.indicators:
            indicator.draw()

        return True

    def run_rest(self, label: str, duration: float | None = None) -> None:
        """
        Repos Stroop personnalisé.

        Le guide est visible pendant le repos, mais disparaît
        indicator_hide_lead secondes avant le prochain stimulus.
        """
        rest_duration = (
            float(duration)
            if duration is not None
            else float(self.design.get("rest_duration", 0.0))
        )

        if rest_duration <= 0:
            return

        # Après le dernier bloc, aucun stimulus ne suit.
        if label == "final":
            self.guide_enabled = False
            self.next_stim_time = None

        else:
            # Temps attendu du prochain onset stimulus :
            #
            # maintenant
            # + repos
            # + instruction de bloc éventuelle
            # + fixation pré-bloc éventuelle
            # + fixation pré-stimulus Stroop
            self.next_stim_time = (
                self.clock.time
                + rest_duration
                + float(self.design.get("instruction_duration", 0.0))
                + float(self.design.get("pre_block_fixation", 0.0))
                + float(self.design.get("fixation_duration", 0.5))
            )

        self.hardware.marker(200)
        self.hardware.eyetracker_message(
            f"REST_START_{label}_t{self.clock.time:.3f}"
        )

        deadline = self.clock.time + rest_duration

        while self.clock.time < deadline:
            self.fixation.draw()
            self.draw_guide()
            self.win.flip()
            self.get_keys([])

        self.hardware.marker(201)
        self.hardware.eyetracker_message(
            f"REST_END_{label}_t{self.clock.time:.3f}"
        )

        # Le repos est fini ; les futurs essais configureront eux-mêmes
        # leur prochain onset.
        self.next_stim_time = None

    def run_trial(self, trial, block_index, trial_index, block) -> dict:
        """
        Déroulement exact d'un essai Stroop :

            fixation pré-stimulus : 500 ms
            stimulus              : 1200 ms
            ITI                   : 300 ms ou jitter event-related

        Le guide :
        - est masqué pendant fixation ;
        - est masqué pendant stimulus ;
        - peut apparaître pendant ITI ;
        - disparaît 2 s avant le stimulus suivant.
        """
        word = trial["word"]
        ink = trial["ink"]
        trial_type = trial["trial_type"]

        fixation_duration = float(self.design["fixation_duration"])
        stim_duration = float(self.design["stim_duration"])

        if self.design.get("paradigm") == "event":
            iti_duration = float(trial["iti"])
        else:
            iti_duration = float(self.design["iti_duration"])

        correct_key = self.response_keys[ink]

        self.flush_keyboard()

        responded = False
        response_key = None
        response_color = None
        rt = None
        guide_shown = False

        # --------------------------------------------------------------
        # 1. Fixation pré-stimulus : guide obligatoirement masqué.
        # --------------------------------------------------------------

        self.next_stim_time = self.clock.time + fixation_duration

        self.fixation.draw()
        self.win.flip()

        fixation_onset = self.clock.time
        fixation_deadline = fixation_onset + fixation_duration

        while self.clock.time < fixation_deadline:
            self.fixation.draw()
            self.win.flip()
            self.get_keys([])

        # --------------------------------------------------------------
        # 2. Stimulus : guide obligatoirement masqué.
        # --------------------------------------------------------------

        self.next_stim_time = None

        self.word_stim.text = word
        self.word_stim.color = self.colors[ink]

        self.word_stim.draw()
        self.win.flip()

        stimulus_onset = self.clock.time

        self.hardware.marker(self.markers.get(trial_type, 0))
        self.hardware.eyetracker_message(
            f"STIM_{trial_type.upper()}_{word}_{ink}_"
            f"B{block_index}_T{trial_index}_"
            f"t{stimulus_onset:.3f}"
        )

        stimulus_deadline = stimulus_onset + stim_duration

        while self.clock.time < stimulus_deadline:
            if not responded:
                keys = self.get_keys(self.valid_keys)

                if keys:
                    response_key = keys[0].name
                    response_color = self.key_to_color.get(response_key)
                    rt = self.clock.time - stimulus_onset
                    responded = True

                    marker = self.markers.get(
                        "correct"
                        if response_color == ink
                        else "incorrect",
                        0,
                    )

                    self.hardware.marker(marker)

            self.word_stim.draw()
            self.win.flip()

        # --------------------------------------------------------------
        # 3. ITI : guide visible si le prochain stimulus est > 2 s.
        # --------------------------------------------------------------

        iti_onset = self.clock.time
        iti_deadline = iti_onset + iti_duration

        is_last_trial = trial_index >= int(block["n_trials"]) - 1

        if is_last_trial:
            # Le prochain événement est un repos, donc le guide peut
            # rester visible pendant toute l'ITI.
            self.next_stim_time = None

        else:
            # Prochain stim = fin ITI + fixation du prochain essai.
            self.next_stim_time = iti_deadline + fixation_duration

        while self.clock.time < iti_deadline:
            if not responded:
                keys = self.get_keys(self.valid_keys)

                if keys:
                    response_key = keys[0].name
                    response_color = self.key_to_color.get(response_key)
                    rt = self.clock.time - stimulus_onset
                    responded = True

                    marker = self.markers.get(
                        "correct"
                        if response_color == ink
                        else "incorrect",
                        0,
                    )

                    self.hardware.marker(marker)

            self.fixation.draw()

            if self.draw_guide():
                guide_shown = True

            self.win.flip()

        self.next_stim_time = None

        is_correct = bool(responded and response_color == ink)

        self.print_trial(
            block_index=block_index,
            trial_index=trial_index,
            onset=stimulus_onset,
            trial_type=trial_type,
            word=word,
            ink=ink,
            response_key=response_key,
            correct=is_correct,
            rt=rt,
        )

        return self.record(
            block_index=block_index,
            trial_index=trial_index,
            block=block,
            onset=stimulus_onset,
            duration=stim_duration,
            trial_type=trial_type,

            word=word,
            ink_color=ink,
            correct_color=ink,
            correct_key=correct_key,

            responded=int(responded),
            response_key=response_key,
            response_color=response_color,
            rt=round(rt, 4) if rt is not None else None,

            is_correct=int(is_correct),
            is_error=int(responded and not is_correct),
            is_miss=int(not responded),

            fixation_onset=round(fixation_onset, 4),
            stimulus_onset=round(stimulus_onset, 4),
            iti_onset=round(iti_onset, 4),

            fixation_duration=fixation_duration,
            stim_duration=stim_duration,
            iti_duration=round(iti_duration, 4),

            guide_shown_in_iti=int(guide_shown),
        )

    @staticmethod
    def print_trial(
        block_index: int,
        trial_index: int,
        onset: float,
        trial_type: str,
        word: str,
        ink: str,
        response_key: str | None,
        correct: bool,
        rt: float | None,
    ) -> None:
        """Affichage console compact d'un essai Stroop."""
        if response_key is None:
            result = "MISS"
            rt_text = "-"
        elif correct:
            result = "OK"
            rt_text = f"{rt * 1000:.0f} ms" if rt is not None else "-"
        else:
            result = "ERR"
            rt_text = f"{rt * 1000:.0f} ms" if rt is not None else "-"

        print(
            f"  B{block_index + 1:02d} "
            f"T{trial_index + 1:02d} "
            f"| t={onset:7.3f} "
            f"| {trial_type[:3].upper():3s} "
            f"| {word:>6s} [{ink[:3]}] "
            f"| resp={response_key or '-':>5s} "
            f"| {result:4s} "
            f"| RT={rt_text}",
            flush=True,
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