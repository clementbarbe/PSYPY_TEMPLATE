"""Classe de base lisible commune aux quatre tâches fMRI."""

from __future__ import annotations

import random
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from core.design import save_design_plan
from core.errors import AbortExperiment, TaskConfigurationError


MARKER_START = 255
MARKER_END = 254
MARKER_REST_START = 200
MARKER_REST_END = 201
MARKER_INSTRUCTION = 210


class BaseTask:
    """Cycle de vie commun d'une tâche PsychoPy.

    Les sous-classes définissent principalement ``setup``, ``instructions``,
    ``build_trials`` et ``run_trial``. Toute la mécanique répétitive (trigger,
    blocs, repos, sauvegarde, logs, Escape, plan expérimental) reste ici.
    """

    NAME = "base"

    def __init__(
        self,
        *,
        win: Any,
        clock: Any,
        settings: Any,
        hardware: Any,
        writer: Any,
        logger: Any,
        task_name: str,
        task_config: dict[str, Any],
        design_id: int,
        run: str,
        seed: int | None = None,
    ) -> None:
        """Initialise les ressources communes sans encore démarrer le timing."""
        from psychopy import visual

        self.win = win
        self.clock = clock
        self.settings = settings
        self.hardware = hardware
        self.writer = writer
        self.logger = logger
        self.task_name = task_name
        self.config = task_config
        self.design_id = int(design_id)
        self.run_id = run
        self.design = self._resolve_design(self.design_id)
        self.blocks = deepcopy(self.design.get("blocks", []))
        if not self.blocks:
            raise TaskConfigurationError(
                f"{task_name}, design {design_id}: aucun bloc défini."
            )

        self.seed = int(seed) if seed is not None else random.SystemRandom().randrange(2**31)
        self.rng = random.Random(self.seed)
        self.global_trial_index = 0
        self.prepared_blocks: list[list[dict[str, Any]]] = []
        self.total_trials = 0

        self.fixation = visual.TextStim(
            self.win, text="+", color="white", height=0.10, pos=(0, 0)
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

    def setup(self) -> None:
        """Crée les stimuli spécifiques ; à surcharger dans la tâche."""

    def instructions(self) -> str:
        """Retourne le texte affiché avant l'attente du trigger."""
        return "Instructions non définies."

    def block_instruction(self, block_index: int, block: dict[str, Any]) -> str | None:
        """Retourne une instruction courte avant un bloc, ou ``None``."""
        del block_index, block
        return None

    def build_trials(self, block: dict[str, Any]) -> list[dict[str, Any]]:
        """Construit les essais d'un bloc ; obligatoire dans chaque tâche."""
        raise NotImplementedError

    def build_all_trials(self) -> list[list[dict[str, Any]]]:
        """Pré-génère tous les essais avant t=0 pour reproductibilité complète."""
        return [self.build_trials(block) for block in self.blocks]

    def validate_trials(self, blocks: list[list[dict[str, Any]]]) -> None:
        """Valide une séquence pré-générée ; surcharge optionnelle."""
        del blocks

    def run_trial(
        self,
        trial: dict[str, Any],
        block_index: int,
        trial_index: int,
        block: dict[str, Any],
    ) -> dict[str, Any]:
        """Présente un essai et retourne son enregistrement comportemental."""
        raise NotImplementedError

    def print_summary(self) -> None:
        """Affiche un résumé terminal ; surcharge optionnelle."""

    @classmethod
    def dry_run(
        cls,
        task_config: dict[str, Any],
        design_id: int,
        seed: int | None = None,
    ) -> None:
        """Valide la structure d'un design sans importer/créer PsychoPy."""
        del seed
        if design_id not in task_config.get("designs", {}):
            raise ValueError(f"Design {design_id} absent.")
        design = task_config["designs"][design_id]
        if not design.get("blocks"):
            raise ValueError("Le design ne définit aucun bloc.")
        for index, block in enumerate(design["blocks"]):
            if int(block.get("n_trials", 0)) < 1:
                raise ValueError(f"Bloc {index + 1}: n_trials doit être >= 1.")

    def run(self) -> Path | None:
        """Exécute le cycle complet, avec sauvegarde finale même après interruption."""
        saved: Path | None = None
        try:
            self.prepare()
            self.show_text_wait(self.instructions())
            self.hardware.eyetracker_start(self.writer.stem)
            self.wait_for_start()
            self.hardware.marker(MARKER_START)
            self.hardware.eyetracker_message("START_EXPERIMENT")

            initial_rest = float(self.design.get("initial_rest_duration", 0.0))
            if initial_rest > 0:
                self.run_rest("initial", duration=initial_rest)

            for block_index, block in enumerate(self.blocks):
                self.run_block(block_index, block)
                if block_index < len(self.blocks) - 1:
                    self.run_rest(f"after_block_{block_index + 1}")

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
            raise
        finally:
            saved = self.finish()
        return saved

    def prepare(self) -> None:
        """Génère, valide et sauvegarde le plan complet avant l'acquisition."""
        self.logger.info(f"Génération du design | seed={self.seed}")
        self.prepared_blocks = self.build_all_trials()
        self.validate_trials(self.prepared_blocks)
        expected = sum(int(block.get("n_trials", 0)) for block in self.blocks)
        produced = sum(len(block) for block in self.prepared_blocks)
        if produced != expected:
            raise TaskConfigurationError(
                f"Séquence invalide : {produced} essais générés, {expected} attendus."
            )
        self.total_trials = produced
        self._write_design_plan()

    def wait_for_start(self) -> None:
        """Attend le trigger scanner puis remet l'horloge expérimentale à zéro."""
        if not self.settings.trigger_enabled or self.settings.mock_mode:
            if self.settings.mock_mode and self.settings.trigger_enabled:
                self.hardware.wait_for_trigger()
            self.clock.reset()
            self.flush_keyboard()
            self.logger.ok(f"t=0 défini ({self.clock.trigger_wall_time})")
            return

        self.text.text = (
            f"Attente du trigger [{self.settings.trigger_key}]\n\n"
            f"{self.settings.quit_key} pour annuler"
        )
        self.text.draw()
        self.win.flip()
        if not self.hardware.wait_for_trigger():
            raise AbortExperiment("Timeout trigger")
        self.clock.reset()
        self.flush_keyboard()
        self.logger.ok(f"Trigger reçu : t=0 ({self.clock.trigger_wall_time})")

    def run_block(self, block_index: int, block: dict[str, Any]) -> None:
        """Exécute instruction, fixation puis tous les essais d'un bloc."""
        instruction = self.block_instruction(block_index, block)
        instruction_duration = float(self.design.get("instruction_duration", 0.0))
        if instruction and instruction_duration > 0:
            self.hardware.marker(MARKER_INSTRUCTION)
            self.show_text_timed(instruction, instruction_duration)

        pre_fixation = float(self.design.get("pre_block_fixation", 0.0))
        if pre_fixation > 0:
            self.show_fixation(pre_fixation)

        trials = self.prepared_blocks[block_index]
        for trial_index, trial in enumerate(trials):
            record = self.run_trial(trial, block_index, trial_index, block)
            record["trial_index_global"] = self.global_trial_index
            self.global_trial_index += 1
            self.writer.write_trial(record)
            self.logger.trial(
                record,
                trial_number=self.global_trial_index,
                total_trials=self.total_trials,
                block_number=block_index + 1,
                total_blocks=len(self.blocks),
            )

    def run_rest(self, label: str, duration: float | None = None) -> None:
        """Présente une fixation de repos et marque son début/sa fin."""
        rest_duration = float(duration) if duration is not None else float(self.design.get("rest_duration", 0.0))
        if rest_duration <= 0:
            return
        self.hardware.marker(MARKER_REST_START)
        self.hardware.eyetracker_message(f"REST_START_{label}_t{self.clock.time:.3f}")
        self.show_fixation(rest_duration)
        self.hardware.marker(MARKER_REST_END)
        self.hardware.eyetracker_message(f"REST_END_{label}_t{self.clock.time:.3f}")

    def finish(self) -> Path | None:
        """Ferme les acquisitions et finalise les fichiers BIDS."""
        try:
            self.hardware.marker(MARKER_END)
            self.hardware.eyetracker_message(f"END_EXPERIMENT_t{self.clock.time:.3f}")
            self.hardware.stop_microphone()
            self.hardware.eyetracker_stop_and_download(self.writer.output_dir)
        except Exception as exc:
            self.logger.warning(f"Cleanup hardware partiel : {exc}")

        saved: Path | None = None
        try:
            saved = self.writer.save_final()
            if saved is not None:
                self.writer.write_sidecar(self._events_sidecar())
        except Exception as exc:
            self.logger.error(f"Finalisation des données impossible : {exc}")
        finally:
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

    def flush_keyboard(self) -> None:
        """Supprime les réponses en attente dans le boîtier/clavier."""
        self.hardware.response_box.clear_events()

    def get_keys(self, key_list: list[str] | None = None) -> list[Any]:
        """Lit les réponses sans bloquer tout en surveillant la touche d'arrêt."""
        if key_list is None:
            keys = self.hardware.response_box.get_keys(None, wait_release=False)
        else:
            check_keys = list(key_list)
            if self.settings.quit_key not in check_keys:
                check_keys.append(self.settings.quit_key)
            keys = self.hardware.response_box.get_keys(check_keys, wait_release=False)

        for key in keys:
            if key.name == self.settings.quit_key:
                raise AbortExperiment(f"{self.settings.quit_key} pressé à t={self.clock.time:.3f}")
        return [key for key in keys if key.name != self.settings.quit_key]

    def show_fixation(self, duration: float) -> None:
        """Affiche la croix de fixation pendant ``duration`` secondes."""
        deadline = self.clock.time + float(duration)
        while self.clock.time < deadline:
            self.fixation.draw()
            self.win.flip()
            self.get_keys([])

    def show_text_wait(self, text: str) -> None:
        """Affiche un texte jusqu'à une réponse quelconque du participant."""
        self.text.text = text
        while True:
            self.text.draw()
            self.win.flip()
            if self.get_keys(None):
                self.flush_keyboard()
                return

    def show_text_timed(self, text: str, duration: float) -> None:
        """Affiche un texte pendant une durée fixe tout en surveillant Escape."""
        self.text.text = text
        deadline = self.clock.time + float(duration)
        while self.clock.time < deadline:
            self.text.draw()
            self.win.flip()
            self.get_keys([])

    def record(
        self,
        *,
        block_index: int,
        trial_index: int,
        block: dict[str, Any],
        onset: float,
        duration: float,
        trial_type: str,
        **fields: Any,
    ) -> dict[str, Any]:
        """Construit un enregistrement uniforme avec temps réel et métadonnées."""
        base: dict[str, Any] = {
            "onset": round(float(onset), 4),
            "duration": round(float(duration), 4),
            "trial_type": str(trial_type),
            "participant": self.settings.participant,
            "session": self.settings.session,
            "run": self.run_id,
            "task": self.task_name,
            "design_id": self.design_id,
            "design_name": self.design.get("name", ""),
            "seed": self.seed,
            "trigger_wall_time": self.clock.trigger_wall_time or "",
            "block_index": block_index,
            "block_condition": block.get("condition", block.get("level", "")),
            "trial_index": trial_index,
            "wall_time": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        }
        base.update(fields)
        if "rt" in base and "response_time" not in base:
            base["response_time"] = base["rt"]
        return base

    def _write_design_plan(self) -> None:
        """Écrit ``_design.json`` et ``_planned_events.tsv`` avant le trigger."""
        if not self.writer.enabled:
            return
        metadata = {
            "task": self.task_name,
            "design_id": self.design_id,
            "design_name": self.design.get("name", ""),
            "participant": self.settings.participant,
            "session": self.settings.session,
            "run": self.run_id,
            "seed": self.seed,
            "paradigm": self.design.get("paradigm", "block"),
            "design_parameters": self.design,
        }
        save_design_plan(
            self.prepared_blocks,
            json_path=self.writer.output_dir / f"{self.writer.stem}_design.json",
            tsv_path=self.writer.output_dir / f"{self.writer.stem}_planned_events.tsv",
            metadata=metadata,
        )
        self.logger.ok("Plan expérimental sauvegardé avant t=0.")

    def _events_sidecar(self) -> dict[str, Any]:
        """Construit le sidecar JSON descriptif du fichier d'événements réel."""
        return {
            "TaskName": self.task_name,
            "DesignID": self.design_id,
            "DesignName": self.design.get("name", ""),
            "Seed": self.seed,
            "Run": self.run_id,
            "TriggerWallTime": self.clock.trigger_wall_time,
            "Columns": {
                "onset": "Onset réel mesuré depuis le trigger scanner t=0, en secondes.",
                "duration": "Durée nominale du stimulus/événement, en secondes.",
                "trial_type": "Condition expérimentale de l'essai.",
                "response_time": "Temps de réponse relatif à l'onset, en secondes quand disponible.",
            },
        }

    def _resolve_design(self, design_id: int) -> dict[str, Any]:
        """Retourne une copie du design demandé ou lève une erreur lisible."""
        designs = self.config.get("designs", {})
        if design_id not in designs:
            available = ", ".join(str(key) for key in sorted(designs))
            raise TaskConfigurationError(
                f"Design {design_id} absent pour {self.task_name}. Disponibles : {available}"
            )
        return deepcopy(designs[design_id])
