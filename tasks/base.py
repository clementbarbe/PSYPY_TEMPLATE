"""
BaseTask — abstract base class for all fMRI tasks.

Template Method pattern:
    setup → instructions → trigger → [blocks] → cleanup

ESCAPE KEY:
    Pressing escape at ANY point raises AbortExperiment.
    The finally block in run() guarantees full cleanup:
    data save, eyetracker transfer, hardware close.

TIMING: t=0 at trigger. All timestamps relative.
DISPLAY: Every loop MUST redraw + flip every frame.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from psychopy import visual
from psychopy.hardware import keyboard

from config.constants import (
    BG_COLOR, TEXT_COLOR, FIXATION_COLOR, INSTRUCTION_COLOR,
    DEFAULT_FONT, FIXATION_HEIGHT, INSTRUCTION_HEIGHT,
    TTL_START_EXP, TTL_END_EXP, TTL_REST_START, TTL_REST_END,
    TTL_INSTRUCTION, END_SCREEN_DURATION, TRIGGER_TIMEOUT,
    QUIT_KEY,
)
from config.settings import ExperimentSettings
from config.scanners.base import ScannerConfig
from core.clock import ExperimentClock
from core.events import EventBus
from core.exceptions import AbortExperiment
from hardware.manager import HardwareManager
from dataio.logger import ExperimentLogger
from dataio.data_writer import DataWriter
from utils.console import SYM_PAUSE


class BaseTask(ABC):
    """Abstract base for all experimental tasks."""

    TASK_NAME: str = 'base'

    def __init__(
        self,
        win: visual.Window,
        clock: ExperimentClock,
        hardware: HardwareManager,
        data_writer: DataWriter,
        logger: ExperimentLogger,
        event_bus: EventBus,
        settings: ExperimentSettings,
        scanner: ScannerConfig,
        task_config: dict,
        design_id: int = 1,
        **kwargs,
    ):
        self.win = win
        self.clock = clock
        self.hardware = hardware
        self.data_writer = data_writer
        self.logger = logger
        self.event_bus = event_bus
        self.settings = settings
        self.scanner = scanner
        self.task_config = task_config

        self.design_id = design_id
        self.design = self._resolve_design(design_id, kwargs)
        self.block_sequence = deepcopy(self.design.get('blocks', []))

        # ── Quit key ─────────────────────────────────────────────────
        self._quit_key = QUIT_KEY

        # ── Common stimuli ───────────────────────────────────────────
        self._fixation = visual.TextStim(
            win, text='+', color=FIXATION_COLOR,
            height=FIXATION_HEIGHT, pos=(0, 0),
        )
        self._instruction_stim = visual.TextStim(
            win, text='', color=INSTRUCTION_COLOR,
            height=INSTRUCTION_HEIGHT, pos=(0, 0),
            wrapWidth=1.5, font=DEFAULT_FONT,
        )

        # ── Keyboard ────────────────────────────────────────────────
        self._keyboard = keyboard.Keyboard(clock=clock.psychopy_clock)
        self._response_keys = dict(scanner.response_keys)
        self._global_trial_idx = 0

        self._setup_stimuli()
        self._log_design_summary()

    # ═════════════════════════════════════════════════════════════════
    # ABSTRACT
    # ═════════════════════════════════════════════════════════════════

    @abstractmethod
    def _setup_stimuli(self) -> None:
        """Create task-specific PsychoPy visual stimuli."""

    @abstractmethod
    def _get_instruction_text(self) -> str:
        """Return full instruction string shown before trigger."""

    @abstractmethod
    def _get_block_instruction(self, block_idx: int,
                               block_def: dict) -> str | None:
        """Return block instruction text, or None to skip."""

    @abstractmethod
    def generate_trials(self, block_def: dict) -> list:
        """Generate ordered trial list for one block."""

    @abstractmethod
    def run_trial(self, trial_data, block_idx: int, trial_idx: int,
                  block_def: dict, **kwargs) -> dict:
        """Execute one trial. Return a record dict."""

    def _print_task_stats(self) -> None:
        """Optional: print task-specific statistics at end."""

    # ═════════════════════════════════════════════════════════════════
    # DESIGN RESOLUTION
    # ═════════════════════════════════════════════════════════════════

    def _resolve_design(self, design_id: int, overrides: dict) -> dict:
        designs = self.task_config.get('designs', {})
        if design_id not in designs:
            available = list(designs.keys())
            raise ValueError(
                f"Design {design_id} not found. Available: {available}"
            )
        design = deepcopy(designs[design_id])
        if 'n_miniblocks' in design and 'miniblock_template' in design:
            template = design.pop('miniblock_template')
            n = design.pop('n_miniblocks')
            design['blocks'] = [deepcopy(template) for _ in range(n)]
        for key, value in overrides.items():
            if value is not None and key in design:
                design[key] = value
        return design

    def _log_design_summary(self) -> None:
        name = self.design.get('name', 'Unknown')
        n_blocks = len(self.block_sequence)
        total_trials = sum(b.get('n_trials', 0) for b in self.block_sequence)
        self.logger.ok(f"{'=' * 60}")
        self.logger.ok(f"TASK: {self.TASK_NAME} | DESIGN: {name}")
        self.logger.ok(f"  Blocks: {n_blocks} | Trials: {total_trials}")
        self.logger.ok(f"{'=' * 60}")

    # ═════════════════════════════════════════════════════════════════
    # KEYBOARD — with escape checking
    # ═════════════════════════════════════════════════════════════════

    def get_keys(self, key_list: list[str] | None = None):
        """
        Get pressed keys (non-blocking).

        ALWAYS checks for the quit key (escape) in addition to
        requested keys. Raises AbortExperiment if quit key pressed.

        Args:
            key_list: keys to return (None = all).
                      Quit key is checked regardless.

        Returns:
            list of KeyPress objects (quit key filtered out).

        Raises:
            AbortExperiment: if quit key is pressed.
        """
        # Build check list: requested keys + quit key
        if key_list is not None:
            check_list = list(key_list)
            if self._quit_key not in check_list:
                check_list.append(self._quit_key)
        else:
            check_list = None  # all keys

        keys = self._keyboard.getKeys(
            keyList=check_list, waitRelease=False,
        )

        if not keys:
            return []

        # Check for quit key
        for key in keys:
            if key.name == self._quit_key:
                self.logger.warn(
                    f"QUIT KEY [{self._quit_key}] pressed "
                    f"at t={self.clock.time:.3f}s — aborting"
                )
                raise AbortExperiment(
                    f"Quit key '{self._quit_key}' pressed"
                )

        # Filter to only requested keys
        if key_list is not None:
            keys = [k for k in keys if k.name in key_list]

        return keys

    def flush_keyboard(self) -> None:
        """Clear all pending keyboard events."""
        self._keyboard.clearEvents()

    # ═════════════════════════════════════════════════════════════════
    # DISPLAY HELPERS — frame-accurate, escape-aware
    # ═════════════════════════════════════════════════════════════════

    def show_fixation(self, duration: float) -> None:
        """Show fixation cross. Escape aborts cleanly."""
        self._fixation.draw()
        self.win.flip()
        deadline = self.clock.time + duration
        while self.clock.time < deadline:
            self._fixation.draw()
            self.win.flip()
            self.get_keys(key_list=[])  # checks escape

    def show_text_and_wait(self, text: str) -> None:
        """Show instruction text and wait for any key press."""
        self._instruction_stim.text = text
        self._instruction_stim.draw()
        self.win.flip()

        # Custom wait loop so we can check escape
        while True:
            self._instruction_stim.draw()
            self.win.flip()
            keys = self._keyboard.getKeys(waitRelease=False)
            if keys:
                for k in keys:
                    if k.name == self._quit_key:
                        raise AbortExperiment(
                            f"Quit key pressed during instructions"
                        )
                break  # any other key → continue

        self.flush_keyboard()

    def show_timed_text(self, text: str, duration: float,
                        stim: visual.TextStim | None = None) -> None:
        """Show text for duration seconds. Escape aborts cleanly."""
        target = stim or self._instruction_stim
        target.text = text
        target.draw()
        self.win.flip()
        deadline = self.clock.time + duration
        while self.clock.time < deadline:
            target.draw()
            self.win.flip()
            self.get_keys(key_list=[])  # checks escape

    # ═════════════════════════════════════════════════════════════════
    # TRIGGER — escape-aware
    # ═════════════════════════════════════════════════════════════════

    def wait_for_trigger(self) -> None:
        """
        Show waiting screen, block until scanner trigger, reset clock.

        Escape key aborts cleanly during the wait.
        """
        trigger_key = self.scanner.trigger_key

        self._instruction_stim.text = (
            f"Attente du trigger [{trigger_key}]...\n\n"
            f"(Appuyez [{self._quit_key}] pour annuler)"
        )
        self._instruction_stim.draw()
        self.win.flip()
        self.logger.log(f"Waiting for trigger (key='{trigger_key}')...")

        # Custom loop: check both trigger key and quit key
        got_trigger = False
        while not got_trigger:
            self._instruction_stim.draw()
            self.win.flip()

            keys = self._keyboard.getKeys(
                keyList=[trigger_key, self._quit_key],
                waitRelease=False,
            )
            for k in (keys or []):
                if k.name == self._quit_key:
                    raise AbortExperiment("Quit during trigger wait")
                if k.name == trigger_key:
                    got_trigger = True
                    break

        # ── t = 0 ────────────────────────────────────────────────────
        self.clock.reset()
        self.flush_keyboard()

        self.logger.ok(
            f"TRIGGER t=0 | {self.clock.trigger_wall_time} | "
            f"scanner={self.scanner.name} | task={self.TASK_NAME}"
        )

        self.hardware.send_trigger(TTL_START_EXP)
        self.hardware.send_eyetracker_message("START_EXP_t0.000")
        self.event_bus.publish('trigger_received')

    # ═════════════════════════════════════════════════════════════════
    # REST
    # ═════════════════════════════════════════════════════════════════

    def run_rest(self, label: str = '', duration: float | None = None) -> None:
        dur = duration if duration is not None else self.design.get(
            'rest_duration', 10.0
        )
        t = self.clock.time
        self.logger.log(f"Rest {dur:.1f}s | {label} | t={t:.3f}s")
        print(f"  {SYM_PAUSE} Rest {dur:.1f}s | t={t:.1f}s | {label}")

        self.hardware.send_trigger(TTL_REST_START)
        self.hardware.send_eyetracker_message(f"REST_START_{label}_t{t:.3f}")

        self.show_fixation(dur)

        self.hardware.send_trigger(TTL_REST_END)
        self.hardware.send_eyetracker_message(
            f"REST_END_{label}_t{self.clock.time:.3f}"
        )

    # ═════════════════════════════════════════════════════════════════
    # BLOCK
    # ═════════════════════════════════════════════════════════════════

    def run_block(self, block_idx: int, block_def: dict) -> None:
        t = self.clock.time
        n_trials = block_def.get('n_trials', 0)

        self.logger.log(
            f"Block {block_idx} | {n_trials} trials | t={t:.3f}s | START"
        )
        self.event_bus.publish(
            'block_start', block_idx=block_idx, block_def=block_def
        )

        instr = self._get_block_instruction(block_idx, block_def)
        instr_dur = self.design.get('instruction_duration', 3.0)
        if instr and instr_dur > 0:
            self.hardware.send_trigger(TTL_INSTRUCTION)
            self.show_timed_text(instr, instr_dur)

        pre_fix = self.design.get('pre_block_fixation', 1.0)
        if pre_fix > 0:
            self.show_fixation(pre_fix)

        trials = self.generate_trials(block_def)
        for trial_idx, trial_data in enumerate(trials):
            record = self.run_trial(
                trial_data,
                block_idx=block_idx,
                trial_idx=trial_idx,
                block_def=block_def,
            )
            record['trial_idx_global'] = self._global_trial_idx
            self._global_trial_idx += 1
            self.data_writer.write_trial(record)
            self.event_bus.publish('trial_end', record=record)

        self.event_bus.publish(
            'block_end', block_idx=block_idx, block_def=block_def
        )
        self.logger.log(f"Block {block_idx} | END")

    # ═════════════════════════════════════════════════════════════════
    # MAIN RUN LOOP — escape + cleanup guarantee
    # ═════════════════════════════════════════════════════════════════

    def run(self) -> Path | None:
        """
        Execute complete task session.

        Escape key or CTRL+C triggers clean shutdown at any point.
        The finally block ALWAYS runs: saves data, closes hardware.
        """
        saved_path = None

        try:
            self.show_text_and_wait(self._get_instruction_text())
            self.wait_for_trigger()
            self.run_rest(label='initial')

            n_blocks = len(self.block_sequence)
            for block_idx, block_def in enumerate(self.block_sequence):
                self.run_block(block_idx, block_def)
                if block_idx < n_blocks - 1:
                    self._run_inter_block(block_idx)

            self.run_rest(label='final')
            self.logger.ok(f"Task {self.TASK_NAME} completed successfully.")

        except AbortExperiment as e:
            self.logger.warn(f"ABORT: {e}")
            print(f"\n  [ABORT] {e}")

        except (KeyboardInterrupt, SystemExit):
            self.logger.warn("Interrupted (CTRL+C or SystemExit).")
            print("\n  [INTERRUPTED] CTRL+C")

        except Exception as e:
            self.logger.err(f"CRITICAL: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # ── GUARANTEED CLEANUP ───────────────────────────────────
            saved_path = self._finish()

        return saved_path

    def _run_inter_block(self, block_idx: int) -> None:
        import random
        paradigm = self.design.get('paradigm', 'block')
        ib_min = self.design.get('inter_block_min', 0.0)
        ib_max = self.design.get('inter_block_max', 0.0)

        if paradigm == 'hybrid' and ib_max > 0:
            jitter = random.uniform(ib_min, ib_max)
            self.run_rest(label=f'jitter_{block_idx}', duration=jitter)
        else:
            self.run_rest(label=f'after_block_{block_idx}')

    # ═════════════════════════════════════════════════════════════════
    # FINISH — guaranteed cleanup
    # ═════════════════════════════════════════════════════════════════

    def _finish(self) -> Path | None:
        """
        End-of-session cleanup. Called from finally block.

        Order:
            1. Send end TTL
            2. Send end eyetracker message
            3. Stop + transfer eyetracker data
            4. Save final CSV
            5. Print stats
            6. Show end screen
            7. Close data writer

        Every step is wrapped in try/except so one failure
        doesn't prevent the others from running.
        """
        t = self.clock.time
        self.logger.log(f"Session end | t={t:.1f}s ({t / 60:.1f} min)")

        # 1. End TTL
        try:
            self.hardware.send_trigger(TTL_END_EXP)
        except Exception:
            pass

        # 2. Eyetracker end message
        try:
            self.hardware.send_eyetracker_message(f"END_EXP_t{t:.3f}")
        except Exception:
            pass

        # 3. Eyetracker: stop, transfer, close
        try:
            if self.hardware.has_eyetracker:
                self.hardware.stop_eyetracker()
                # Transfer data to subject directory
                data_dir = self.settings.task_dir(self.TASK_NAME)
                if self.hardware._eyetracker is not None:
                    self.hardware._eyetracker.transfer_data(str(data_dir))
        except Exception as e:
            self.logger.warn(f"Eyetracker cleanup: {e}")

        # 4. Save final CSV
        saved = None
        try:
            saved = self.data_writer.save_final()
        except Exception as e:
            self.logger.err(f"Final save failed: {e}")

        # 5. Close data writer
        try:
            self.data_writer.close()
        except Exception:
            pass

        # 6. Stats
        try:
            if self.data_writer.records:
                self._print_task_stats()
        except Exception:
            pass

        # 7. End screen
        try:
            if self.win and not getattr(self.win, '_closed', False):
                self._instruction_stim.text = (
                    "Fin de la session.\nMerci pour votre participation."
                )
                self._instruction_stim.draw()
                self.win.flip()
                self.clock.wait(END_SCREEN_DURATION)
        except Exception:
            pass

        self.event_bus.publish('task_end', saved_path=saved)
        return saved

    # ═════════════════════════════════════════════════════════════════
    # COMMON RECORD FIELDS
    # ═════════════════════════════════════════════════════════════════

    def _base_record(self, block_idx: int, trial_idx: int,
                     block_def: dict) -> dict:
        return {
            'participant': self.settings.participant_id,
            'session': self.settings.session,
            'run': self.settings.run,
            'scanner': self.scanner.name,
            'mode': self.settings.mode,
            'design_id': self.design_id,
            'design_name': self.design.get('name', ''),
            'trigger_time': self.clock.trigger_wall_time or '',
            'block_idx': block_idx,
            'trial_idx': trial_idx,
            'task_time': round(self.clock.time, 4),
            'wall_timestamp': datetime.now().strftime('%H:%M:%S.%f'),
        }