"""
BaseTask : logique commune à toutes les tâches.

Les tâches doivent définir au minimum :

    class Task(BaseTask):
        def setup(self): ...
        def instructions(self): ...
        def build_trials(self, block): ...
        def run_trial(self, trial, block_index, trial_index, block): ...
"""

from __future__ import annotations

import json
import random
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from psychopy import visual
from psychopy.hardware import keyboard

from experiment import AbortExperiment, TaskConfigurationError


MARKER_START = 255
MARKER_END = 254
MARKER_REST_START = 200
MARKER_REST_END = 201
MARKER_INSTRUCTION = 210


class BaseTask:
    """Base simple et réutilisable pour les tâches PsychoPy."""

    NAME = "base"
    PREGENERATE = False

    def __init__(
        self,
        win,
        clock,
        settings,
        hardware,
        writer,
        logger,
        task_name: str,
        task_config: dict,
        design_id: int,
        run: str,
        seed: int | None = None,
    ):
        self.win = win
        self.clock = clock
        self.settings = settings
        self.hardware = hardware
        self.writer = writer
        self.logger = logger

        self.task_name = task_name
        self.config = task_config
        self.design_id = design_id
        self.run_id = run

        self.design = self._resolve_design(design_id)
        self.blocks = deepcopy(self.design.get("blocks", []))

        if not self.blocks:
            raise TaskConfigurationError(
                f"{task_name}, design {design_id}: aucun bloc défini."
            )

        self.seed = seed if seed is not None else random.randrange(2**31)
        self.rng = random.Random(self.seed)

        self.global_trial_index = 0
        self.prepared_blocks: list[list] | None = None

        self.keyboard = keyboard.Keyboard(clock=self.clock.psychopy_clock)

        self.fixation = visual.TextStim(
            self.win,
            text="+",
            color="white",
            height=0.10,
            pos=(0, 0),
        )

        self.text = visual.TextStim(
            self.win,
            text="",
            color=(1, 1, 0),
            height=0.055,
            pos=(0, 0),
            wrapWidth=1.55,
            font="Arial",
        )

        self.setup()

    # ------------------------------------------------------------------
    # Méthodes à définir par les tâches
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """Crée les stimuli spécifiques de la tâche."""

    def instructions(self) -> str:
        """Texte affiché avant le trigger."""
        return "Instructions non définies."

    def block_instruction(self, block_index: int, block: dict) -> str | None:
        """Instruction courte avant un bloc, ou None."""
        return None

    def build_trials(self, block: dict) -> list:
        """Génère les essais d'un bloc."""
        raise NotImplementedError

    def build_all_trials(self) -> list[list]:
        """Optionnel : génération complète avant t=0."""
        return [self.build_trials(block) for block in self.blocks]

    def validate_trials(self, blocks: list[list]) -> None:
        """Optionnel : lève une erreur si la séquence est invalide."""

    def run_trial(
        self,
        trial,
        block_index: int,
        trial_index: int,
        block: dict,
    ) -> dict:
        """Exécute un essai et retourne son dictionnaire de données."""
        raise NotImplementedError

    def print_summary(self) -> None:
        """Optionnel : résumé terminal à la fin."""

    # ------------------------------------------------------------------
    # Validation hors PsychoPy
    # ------------------------------------------------------------------

    @classmethod
    def dry_run(
        cls,
        task_config: dict,
        design_id: int,
        seed: int | None = None,
    ) -> None:
        """
        Validation de la configuration sans créer de fenêtre PsychoPy.

        Les tâches complexes peuvent surcharger cette méthode.
        """
        if design_id not in task_config["designs"]:
            raise ValueError(f"Design {design_id} absent.")

        design = task_config["designs"][design_id]

        if not design.get("blocks"):
            raise ValueError("Le design ne définit aucun bloc.")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def run(self) -> Path | None:
        """
        Exécute la tâche.

        Important :
        - aucun repos initial implicite après le trigger ;
        - aucun repos final implicite ;
        - les repos entre blocs restent contrôlés par les tâches/designs ;
        - un design peut demander explicitement un repos initial/final
        avec initial_rest_duration / final_rest_duration.
        """
        saved = None

        try:
            self.prepare()
            self.show_text_wait(self.instructions())
            self.wait_for_start()

            self.hardware.marker(MARKER_START)
            self.hardware.eyetracker_message("START_EXPERIMENT")

            # Repos initial UNIQUEMENT s'il est explicitement demandé.
            initial_rest = float(self.design.get("initial_rest_duration", 0.0))

            if initial_rest > 0:
                self.run_rest("initial", duration=initial_rest)

            # Blocs expérimentaux.
            for block_index, block in enumerate(self.blocks):
                self.run_block(block_index, block)

                # Repos uniquement ENTRE les blocs.
                if block_index < len(self.blocks) - 1:
                    self.run_rest(f"after_block_{block_index + 1}")

            # Repos final UNIQUEMENT s'il est explicitement demandé.
            final_rest = float(self.design.get("final_rest_duration", 0.0))

            if final_rest > 0:
                self.run_rest("final", duration=final_rest)

            self.logger.ok("Tâche terminée normalement.")

        except AbortExperiment as exc:
            self.logger.warning(f"Tâche interrompue : {exc}")

        except KeyboardInterrupt:
            self.logger.warning("Tâche interrompue par l'utilisateur.")

        except Exception as exc:
            import traceback

            self.logger.error(f"Erreur critique : {exc}")
            traceback.print_exc()

        finally:
            saved = self.finish()

        return saved

    def prepare(self) -> None:
        if not self.PREGENERATE:
            return

        self.logger.info(f"Génération de séquence, seed={self.seed}")

        self.prepared_blocks = self.build_all_trials()
        self.validate_trials(self.prepared_blocks)

        expected = sum(block.get("n_trials", 0) for block in self.blocks)
        produced = sum(len(block) for block in self.prepared_blocks)

        if produced != expected:
            raise TaskConfigurationError(
                f"Séquence invalide : {produced} essais générés, "
                f"{expected} attendus."
            )

        self.write_design_sidecar()

    def wait_for_start(self) -> None:
        if not self.settings.trigger_enabled:
            self.clock.reset()
            self.flush_keyboard()
            return

        self.text.text = (
            f"Attente du trigger [{self.settings.trigger_key}]\n\n"
            f"Escape pour annuler"
        )

        self.text.draw()
        self.win.flip()

        received = self.hardware.wait_for_trigger(
            keyboard=self.keyboard,
            quit_key=self.settings.quit_key,
        )

        if not received:
            raise AbortExperiment("Timeout trigger")

        self.clock.reset()
        self.flush_keyboard()

        self.logger.ok(f"Trigger reçu : t=0 ({self.clock.trigger_wall_time})")

    def run_block(self, block_index: int, block: dict) -> None:
        instruction = self.block_instruction(block_index, block)
        instruction_duration = float(self.design.get("instruction_duration", 0))

        if instruction and instruction_duration > 0:
            self.hardware.marker(MARKER_INSTRUCTION)
            self.show_text_timed(instruction, instruction_duration)

        pre_fixation = float(self.design.get("pre_block_fixation", 0))

        if pre_fixation > 0:
            self.show_fixation(pre_fixation)

        if self.prepared_blocks is not None:
            trials = self.prepared_blocks[block_index]
        else:
            trials = self.build_trials(block)

        for trial_index, trial in enumerate(trials):
            record = self.run_trial(
                trial=trial,
                block_index=block_index,
                trial_index=trial_index,
                block=block,
            )

            record["trial_index_global"] = self.global_trial_index
            self.global_trial_index += 1

            self.writer.write_trial(record)

    def run_rest(self, label: str, duration: float | None = None) -> None:
        rest_duration = (
            float(duration)
            if duration is not None
            else float(self.design.get("rest_duration", 0))
        )

        if rest_duration <= 0:
            return

        self.hardware.marker(MARKER_REST_START)
        self.hardware.eyetracker_message(
            f"REST_START_{label}_t{self.clock.time:.3f}"
        )

        self.show_fixation(rest_duration)

        self.hardware.marker(MARKER_REST_END)
        self.hardware.eyetracker_message(
            f"REST_END_{label}_t{self.clock.time:.3f}"
        )

    def finish(self) -> Path | None:
        self.hardware.marker(MARKER_END)
        self.hardware.eyetracker_message(f"END_EXPERIMENT_t{self.clock.time:.3f}")

        try:
            self.hardware.stop_microphone(self.clock)
        except Exception:
            pass

        try:
            self.hardware.eyetracker_stop_and_download(self.writer.output_dir)
        except Exception:
            pass

        saved = self.writer.save_final()
        self.writer.close()

        try:
            self.print_summary()
        except Exception as exc:
            self.logger.warning(f"Résumé impossible : {exc}")

        try:
            self.show_text_timed(
                "Fin de la session.\n\nMerci pour votre participation.",
                self.settings.end_screen_seconds,
            )
        except Exception:
            pass

        return saved

    # ------------------------------------------------------------------
    # Helpers écran / clavier
    # ------------------------------------------------------------------

    def flush_keyboard(self) -> None:
        self.keyboard.clearEvents()

    def get_keys(self, key_list: list[str] | None = None):
        """
        Lit le clavier sans bloquer.

        Règles :
        - key_list=None : accepte toutes les touches, avec Escape surveillé.
        Utilisé pour les écrans d'instructions « Appuyez sur une touche ».
        - key_list=[] : surveille uniquement Escape.
        Utilisé pendant les périodes où aucune réponse ne doit être prise.
        - key_list=["left", "right"] : accepte ces touches et surveille Escape.
        """
        # None signifie réellement « toutes les touches ».
        if key_list is None:
            keys = self.keyboard.getKeys(
                keyList=None,
                waitRelease=False,
            )

        else:
            # [] signifie « aucune réponse comportementale, Escape seulement ».
            check_keys = list(key_list)

            if self.settings.quit_key not in check_keys:
                check_keys.append(self.settings.quit_key)

            keys = self.keyboard.getKeys(
                keyList=check_keys,
                waitRelease=False,
            )

        for key in keys:
            if key.name == self.settings.quit_key:
                raise AbortExperiment(
                    f"Escape pressé à t={self.clock.time:.3f}"
                )

        # Pendant instructions : renvoyer toute touche sauf Escape.
        if key_list is None:
            return [
                key for key in keys
                if key.name != self.settings.quit_key
            ]

        # Pendant un essai : renvoyer seulement les touches de réponse.
        return [
            key for key in keys
            if key.name != self.settings.quit_key
        ]

    def show_fixation(self, duration: float) -> None:
        deadline = self.clock.time + duration

        while self.clock.time < deadline:
            self.fixation.draw()
            self.win.flip()
            self.get_keys([])

    def show_text_wait(self, text: str) -> None:
        self.text.text = text

        while True:
            self.text.draw()
            self.win.flip()

            keys = self.get_keys(None)

            if keys:
                self.flush_keyboard()
                return

    def show_text_timed(self, text: str, duration: float) -> None:
        self.text.text = text
        deadline = self.clock.time + duration

        while self.clock.time < deadline:
            self.text.draw()
            self.win.flip()
            self.get_keys([])

    # ------------------------------------------------------------------
    # Enregistrement
    # ------------------------------------------------------------------

    def record(
        self,
        block_index: int,
        trial_index: int,
        block: dict,
        onset: float,
        duration: float,
        trial_type: str,
        **fields,
    ) -> dict:
        """Crée un record uniforme pour toutes les tâches."""

        base = {
            "onset": round(onset, 4),
            "duration": round(duration, 4),
            "trial_type": trial_type,
            "participant": self.settings.participant,
            "session": self.settings.session,
            "run": self.run_id,
            "task": self.task_name,
            "design_id": self.design_id,
            "design_name": self.design.get("name", ""),
            "seed": self.seed,
            "trigger_wall_time": self.clock.trigger_wall_time or "",
            "block_index": block_index,
            "block_condition": block.get("condition", ""),
            "trial_index": trial_index,
            "wall_time": datetime.now().isoformat(timespec="milliseconds"),
        }

        base.update(fields)
        return base

    def write_design_sidecar(self) -> None:
        payload = {
            "task": self.task_name,
            "design_id": self.design_id,
            "design_name": self.design.get("name", ""),
            "run": self.run_id,
            "participant": self.settings.participant,
            "session": self.settings.session,
            "seed": self.seed,
            "design": self.design,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        path = self.writer.output_dir / f"{self.writer.stem}_design.json"

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            self.logger.warning(f"Sidecar design non écrit : {exc}")

    def _resolve_design(self, design_id: int) -> dict:
        designs = self.config.get("designs", {})

        if design_id not in designs:
            available = ", ".join(str(key) for key in sorted(designs))
            raise TaskConfigurationError(
                f"Design {design_id} absent pour {self.task_name}. "
                f"Disponibles : {available}"
            )

        return deepcopy(designs[design_id])