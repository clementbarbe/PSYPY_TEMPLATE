"""Classe de base lisible commune aux quatre tâches fMRI."""

from __future__ import annotations

import random
import math
import sys
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
        session_metadata: dict[str, Any] | None = None,
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
        self.run_id = run
        self._init_design(task_config, design_id, seed)
        self.metadata = dict(session_metadata or {})
        self.run_status = "preparing"
        self.stop_reason: str | None = None
        self.run_end_time: float | None = None
        self.cleanup_errors: list[str] = []
        self.eyetracker_file: str | None = None
        self.remote_edf: str | None = None
        self.current_block: int | None = None
        self.current_trial: int | None = None

        self.fixation = visual.TextStim(
            self.win, text="+", color="white", height=0.10, pos=(0, 0)
        )
        self.text = visual.TextStim(
            self.win, text="", color=(1, 1, 0), height=0.055,
            pos=(0, 0), wrapWidth=1.55, font="Arial",
        )
        self.setup()

    def _init_design(self, task_config: dict, design_id: int, seed: int | None) -> None:
        """Initialise la génération pure, commune au dry-run et à l'acquisition."""
        self.config = deepcopy(task_config)
        self.design_id = int(design_id)
        self.design = self._resolve_design(self.design_id)
        self.design.setdefault("final_rest_duration", 10.0)
        self.blocks = deepcopy(self.design.get("blocks", []))
        if not self.blocks:
            raise TaskConfigurationError(f"Design {design_id}: aucun bloc défini.")
        for block in self.blocks:
            if int(block.get("n_trials", 0)) < 1:
                raise TaskConfigurationError("Chaque bloc doit contenir au moins un essai.")
        for key, value in self.design.items():
            if key.endswith(("duration", "_min", "_max", "fixation")) and isinstance(value, (int, float)):
                if not math.isfinite(value) or value < 0:
                    raise TaskConfigurationError(f"Durée invalide : {key}={value}")
        if float(self.design["final_rest_duration"]) < 10:
            raise TaskConfigurationError("Prévoir au moins 10 s de repos final pour l'IRMf.")
        self.seed = int(seed) if seed is not None else random.SystemRandom().randrange(2**31)
        self.rng = random.Random(self.seed)
        self.global_trial_index = 0
        self.prepared_blocks: list[list[dict[str, Any]]] = []
        self.total_trials = 0

        self.setup_design()

    def setup_design(self) -> None:
        """Prépare les paramètres scientifiques sans importer PsychoPy."""

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
        """Génère et valide exactement les essais utilisés en acquisition."""
        task = cls.__new__(cls)
        task._init_design(task_config, design_id, seed)
        task._generate_trials()

    def run(self) -> Path | None:
        """Exécute le cycle complet, avec sauvegarde finale même après interruption."""
        saved: Path | None = None
        try:
            self.prepare()
            self.show_text_wait(self.instructions())
            self.hardware.eyetracker_start(self.writer.stem)
            self.remote_edf = getattr(self.hardware.eyetracker, "remote_filename", None)
            self.writer.write_run_metadata(self._run_metadata())
            self.wait_for_start()
            self.run_status = "running"
            self.win.recordFrameIntervals = True
            if self.settings.microphone_enabled:
                self.hardware.start_microphone(self.writer.output_dir / f"{self.writer.stem}_audio.wav")
            self.hardware.marker(MARKER_START)
            self.hardware.eyetracker_message("START_EXPERIMENT")

            initial_rest = float(self.design.get("initial_rest_duration", 0.0))
            if initial_rest > 0:
                self.run_rest("initial", duration=initial_rest)

            for block_index, block in enumerate(self.blocks):
                self.run_block(block_index, block)
                if block_index < len(self.blocks) - 1:
                    self.run_rest(f"after_block_{block_index + 1}")

            final_rest = float(self.design["final_rest_duration"])
            if final_rest > 0:
                self.run_rest("final", duration=final_rest)
            if self.global_trial_index != self.total_trials:
                raise RuntimeError("Le nombre d'essais exécutés ne correspond pas au plan.")
            self.run_status = "completed"
            self.logger.ok("Tâche terminée normalement.")
        except AbortExperiment as exc:
            self.run_status, self.stop_reason = "aborted", str(exc)
            self.logger.warning(f"Tâche interrompue : {exc}")
            raise
        except KeyboardInterrupt:
            self.run_status, self.stop_reason = "aborted", "KeyboardInterrupt"
            self.logger.warning("Tâche interrompue par l'utilisateur.")
            raise AbortExperiment(self.stop_reason)
        except Exception as exc:
            import traceback

            self.run_status, self.stop_reason = "failed", str(exc)
            self.logger.error(traceback.format_exc())
            raise
        finally:
            active_error = sys.exc_info()[1]
            self.run_end_time = self.clock.time if self.clock.trigger_wall_time else None
            self.win.recordFrameIntervals = False
            try:
                saved = self.finish()
            except Exception as exc:
                if active_error is None:
                    raise
                self.logger.error(f"Erreur supplémentaire en finalisation : {exc}")
        return saved

    def prepare(self) -> None:
        """Génère, valide et sauvegarde le plan complet avant l'acquisition."""
        self.logger.info(f"Génération du design | seed={self.seed}")
        self.writer.write_run_metadata(self._run_metadata())
        self._generate_trials()
        self._write_design_plan()
        self.writer.write_run_metadata(self._run_metadata())

    def _generate_trials(self) -> None:
        """Vérifie les contraintes et les comptes de chaque bloc pré-généré."""
        self.prepared_blocks = self.build_all_trials()
        self.validate_trials(self.prepared_blocks)
        expected = sum(int(block.get("n_trials", 0)) for block in self.blocks)
        produced = sum(len(block) for block in self.prepared_blocks)
        if len(self.prepared_blocks) != len(self.blocks) or any(
            len(trials) != int(block["n_trials"])
            for trials, block in zip(self.prepared_blocks, self.blocks)
        ) or produced != expected:
            raise TaskConfigurationError(
                f"Séquence invalide : {produced} essais générés, {expected} attendus."
            )
        self.total_trials = produced

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
        self.clock.reset(self.hardware.trigger.last_trigger_time)
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
            self.current_block, self.current_trial = block_index, trial_index
            self.hardware.eyetracker_message(f"TRIAL_START B{block_index}_T{trial_index}")
            record = self.run_trial(trial, block_index, trial_index, block)
            self.hardware.eyetracker_message(f"TRIAL_END B{block_index}_T{trial_index}")
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
        actions = [
            lambda: self.hardware.audio.close() if self.hardware._audio is not None else None,
            lambda: self.hardware.marker(MARKER_END) if self.clock.trigger_wall_time else None,
            lambda: self.hardware.eyetracker_message(f"END_EXPERIMENT status={self.run_status} t={self.clock.time:.6f}"),
            self.hardware.stop_microphone,
            lambda: self.hardware.eyetracker_stop_and_download(self.writer.output_dir),
        ]
        for index, action in enumerate(actions):
            try:
                result = action()
                if index == 4 and result is not None:
                    self.eyetracker_file = str(result)
            except Exception as exc:
                self.cleanup_errors.append(str(exc))
                self.logger.error(f"Finalisation hardware : {exc}")
        if self.cleanup_errors:
            self.run_status = "failed"

        saved: Path | None = None
        try:
            saved = self.writer.save_final()
            if saved is not None:
                self.writer.write_sidecar(self._events_sidecar())
        except Exception as exc:
            self.run_status = "failed"
            self.cleanup_errors.append(str(exc))
            self.logger.error(f"Finalisation des données impossible : {exc}")
        finally:
            try:
                self.writer.write_run_metadata(self._run_metadata())
            except Exception as exc:
                self.cleanup_errors.append(str(exc))
                self.logger.error(f"Métadonnées de run non sauvegardées : {exc}")
            finally:
                self.writer.close()

        try:
            self.print_summary()
        except Exception as exc:
            self.logger.warning(f"Résumé impossible : {exc}")
        try:
            self.show_text_timed(
                "Fin du run." if self.run_status == "completed" else "Run interrompu ou en erreur.\nPrévenir l'expérimentateur.",
                self.settings.end_screen_seconds,
            )
        except Exception:
            pass
        if self.cleanup_errors:
            raise RuntimeError("Finalisation incomplète : " + "; ".join(self.cleanup_errors))
        return saved

    def flush_keyboard(self) -> None:
        """Supprime les réponses en attente dans le boîtier/clavier."""
        self.hardware.response_box.clear_events()
        self._pending_response_keys = []

    def get_keys(self, key_list: list[str] | None = None) -> list[Any]:
        """Lit les réponses sans bloquer tout en surveillant la touche d'arrêt."""
        if key_list is None:
            keys = self.hardware.get_keys(None)
        else:
            check_keys = list(key_list)
            if self.settings.quit_key not in check_keys:
                check_keys.append(self.settings.quit_key)
            keys = self.hardware.get_keys(check_keys)

        for key in keys:
            if key.name == self.settings.quit_key:
                raise AbortExperiment(f"{self.settings.quit_key} pressé à t={self.clock.time:.3f}")
        return [key for key in keys if key.name != self.settings.quit_key]

    def poll_response(self, onset: float, deadline: float, responded: bool = False) -> Any:
        """Surveille Escape et retient le premier appui horodaté dans la fenêtre."""
        keys = self.get_keys([] if responded else self.valid_keys)
        if not responded:
            keys = getattr(self, "_pending_response_keys", []) + keys
            self._pending_response_keys = [key for key in keys if key.rt is not None and self.clock.event_time(key.rt) >= deadline]
        valid = [key for key in keys if key.rt is not None and onset <= self.clock.event_time(key.rt) < deadline]
        return min(valid, key=lambda key: key.rt) if valid else None

    def flip(self) -> float:
        """Affiche une frame et conserve son timestamp dans l'horloge du run."""
        timestamp = self.win.flip()
        if timestamp is None:
            raise RuntimeError("Le flip n'a pas fourni de timestamp (waitBlanking requis).")
        return self.clock.flip_time(timestamp)

    def show_fixation(self, duration: float) -> None:
        """Affiche la croix de fixation pendant ``duration`` secondes."""
        deadline = self.clock.time + float(duration)
        while self.clock.time < deadline:
            self.fixation.draw()
            self.win.flip()
            self.get_keys([])

    def show_text_wait(self, text: str) -> None:
        """Attend uniquement la touche opérateur avant d'armer le trigger."""
        self.text.text = text + f"\n\nExpérimentateur : [{self.settings.operator_start_key}] pour autoriser l'attente du trigger."
        self.hardware.keyboard.clear_events()
        while True:
            self.text.draw()
            self.win.flip()
            keys = self.hardware.keyboard.get_keys([self.settings.operator_start_key, self.settings.quit_key], wait_release=False)
            if any(key.name == self.settings.quit_key for key in keys):
                raise AbortExperiment("Interruption avant autorisation du trigger.")
            if any(key.name == self.settings.operator_start_key for key in keys):
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
            "task_configuration": self.config,
            "session_metadata": self.metadata,
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
            **self._run_metadata(),
            "TaskName": self.task_name,
            "DesignID": self.design_id,
            "DesignName": self.design.get("name", ""),
            "Seed": self.seed,
            "Run": self.run_id,
            "TriggerWallTime": self.clock.trigger_wall_time,
            "Columns": {
                "onset": "Timestamp logiciel du flip visuel ou début audio programmé, relatif au trigger en secondes ; voir onset_reference.",
                "duration": "Durée nominale du stimulus/événement, en secondes.",
                "trial_type": "Condition expérimentale de l'essai.",
                "response_time": "Temps de réponse relatif à l'onset, en secondes quand disponible.",
            },
        }

    def _run_metadata(self) -> dict[str, Any]:
        """Décrit l'acquisition, sa complétude et les sorties effectivement produites."""
        return {
            **self.metadata, "task": self.task_name, "design_id": self.design_id,
            "participant": self.settings.participant, "session": self.settings.session,
            "run": self.run_id, "seed": self.seed, "status": self.run_status,
            "stop_reason": self.stop_reason, "cleanup_errors": list(self.cleanup_errors),
            "expected_trials": sum(int(b["n_trials"]) for b in self.blocks),
            "completed_trials": self.writer.n_trials,
            "last_block": self.current_block, "last_trial": self.current_trial,
            "trigger_wall_time": self.clock.trigger_wall_time, "run_duration": self.run_end_time,
            "remote_edf": self.remote_edf, "eyetracker_file": self.eyetracker_file,
            "marker_events": list(self.hardware.marker_events),
            "dropped_frames": getattr(self.win, "nDroppedFrames", None),
            "task_configuration": self.config,
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
