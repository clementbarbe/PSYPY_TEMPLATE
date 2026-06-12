"""
BaseTask — abstract base class with escape handling and audio support.

Template Method: setup -> instructions -> trigger -> [blocks] -> cleanup

ESCAPE: raises AbortExperiment at any point, triggers full cleanup.
AUDIO: self.audio provides lazy AudioManager access.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from psychopy import visual
from psychopy.hardware import keyboard

from config.constants import (
    FIXATION_COLOR, INSTRUCTION_COLOR,
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

        self._quit_key = QUIT_KEY
        self._audio = None  # lazy init

        self._fixation = visual.TextStim(
            win, text='+', color=FIXATION_COLOR,
            height=FIXATION_HEIGHT, pos=(0, 0),
        )
        self._instruction_stim = visual.TextStim(
            win, text='', color=INSTRUCTION_COLOR,
            height=INSTRUCTION_HEIGHT, pos=(0, 0),
            wrapWidth=1.5, font=DEFAULT_FONT,
        )

        self._keyboard = keyboard.Keyboard(clock=clock.psychopy_clock)
        self._response_keys = dict(scanner.response_keys)
        self._global_trial_idx = 0

        self._setup_stimuli()
        self._log_design_summary()

    # ═════════════════════════════════════════════════════════════════
    # AUDIO — lazy init
    # ═════════════════════════════════════════════════════════════════

    @property
    def audio(self):
        """
        Lazy AudioManager access.

        Only created on first use — tasks that don't need audio
        pay no cost. Usage in subclass::

            def _setup_stimuli(self):
                self.audio.preload('beep', 'stimuli/sounds/beep.wav')

            def run_trial(self, ...):
                self.audio.play_scheduled('beep', target_t, self.clock)
        """
        if self._audio is None:
            from hardware.audio import AudioManager
            self._audio = AudioManager()
            self.logger.log("AudioManager initialised (lazy).")
        return self._audio

    # ═════════════════════════════════════════════════════════════════
    # ABSTRACT
    # ═════════════════════════════════════════════════════════════════

    @abstractmethod
    def _setup_stimuli(self) -> None:
        """Create task-specific visual stimuli."""

    @abstractmethod
    def _get_instruction_text(self) -> str:
        """Return instruction string."""

    @abstractmethod
    def _get_block_instruction(self, block_idx: int,
                               block_def: dict) -> str | None:
        """Return block instruction, or None to skip."""

    @abstractmethod
    def generate_trials(self, block_def: dict) -> list:
        """Generate trial list for one block."""

    @abstractmethod
    def run_trial(self, trial_data, block_idx: int, trial_idx: int,
                  block_def: dict, **kwargs) -> dict:
        """Execute one trial. Return record dict."""

    def _print_task_stats(self) -> None:
        """Optional end stats."""

    # ═════════════════════════════════════════════════════════════════
    # DESIGN
    # ═════════════════════════════════════════════════════════════════

    def _resolve_design(self, design_id: int, overrides: dict) -> dict:
        designs = self.task_config.get('designs', {})
        if design_id not in designs:
            raise ValueError(
                f"Design {design_id} not found. Available: {list(designs.keys())}"
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
        n = len(self.block_sequence)
        t = sum(b.get('n_trials', 0) for b in self.block_sequence)
        self.logger.ok(f"TASK: {self.TASK_NAME} | DESIGN: {name} | {n} blocks | {t} trials")

    # ═════════════════════════════════════════════════════════════════
    # KEYBOARD — escape-aware
    # ═════════════════════════════════════════════════════════════════

    def get_keys(self, key_list: list[str] | None = None):
        """Get keys, checking escape. Raises AbortExperiment on escape."""
        if key_list is not None:
            check = list(key_list)
            if self._quit_key not in check:
                check.append(self._quit_key)
        else:
            check = None

        keys = self._keyboard.getKeys(keyList=check, waitRelease=False)
        if not keys:
            return []

        for k in keys:
            if k.name == self._quit_key:
                raise AbortExperiment(f"Escape pressed at t={self.clock.time:.3f}s")

        if key_list is not None:
            keys = [k for k in keys if k.name in key_list]
        return keys

    def flush_keyboard(self) -> None:
        self._keyboard.clearEvents()

    # ═════════════════════════════════════════════════════════════════
    # DISPLAY
    # ═════════════════════════════════════════════════════════════════

    def show_fixation(self, duration: float) -> None:
        self._fixation.draw()
        self.win.flip()
        deadline = self.clock.time + duration
        while self.clock.time < deadline:
            self._fixation.draw()
            self.win.flip()
            self.get_keys(key_list=[])

    def show_text_and_wait(self, text: str) -> None:
        self._instruction_stim.text = text
        self._instruction_stim.draw()
        self.win.flip()
        while True:
            self._instruction_stim.draw()
            self.win.flip()
            keys = self._keyboard.getKeys(waitRelease=False)
            if keys:
                for k in keys:
                    if k.name == self._quit_key:
                        raise AbortExperiment("Escape during instructions")
                break
        self.flush_keyboard()

    def show_timed_text(self, text: str, duration: float,
                        stim=None) -> None:
        target = stim or self._instruction_stim
        target.text = text
        target.draw()
        self.win.flip()
        deadline = self.clock.time + duration
        while self.clock.time < deadline:
            target.draw()
            self.win.flip()
            self.get_keys(key_list=[])

    # ═════════════════════════════════════════════════════════════════
    # TRIGGER
    # ═════════════════════════════════════════════════════════════════

    def wait_for_trigger(self) -> None:
        trigger_key = self.scanner.trigger_key
        self._instruction_stim.text = f"Attente trigger [{trigger_key}]..."
        self._instruction_stim.draw()
        self.win.flip()

        while True:
            self._instruction_stim.draw()
            self.win.flip()
            keys = self._keyboard.getKeys(
                keyList=[trigger_key, self._quit_key], waitRelease=False,
            )
            for k in (keys or []):
                if k.name == self._quit_key:
                    raise AbortExperiment("Escape during trigger wait")
                if k.name == trigger_key:
                    self.clock.reset()
                    self.flush_keyboard()
                    self.logger.ok(f"TRIGGER t=0 | {self.clock.trigger_wall_time}")
                    self.hardware.send_trigger(TTL_START_EXP)
                    self.hardware.send_eyetracker_message("START_EXP_t0.000")
                    self.event_bus.publish('trigger_received')
                    return

    # ═════════════════════════════════════════════════════════════════
    # REST / BLOCK
    # ═════════════════════════════════════════════════════════════════

    def run_rest(self, label='', duration=None):
        dur = duration if duration is not None else self.design.get('rest_duration', 10.0)
        t = self.clock.time
        print(f"  {SYM_PAUSE} Rest {dur:.1f}s | t={t:.1f}s | {label}")
        self.hardware.send_trigger(TTL_REST_START)
        self.show_fixation(dur)
        self.hardware.send_trigger(TTL_REST_END)

    def run_block(self, block_idx: int, block_def: dict) -> None:
        self.logger.log(f"Block {block_idx} | START")
        self.event_bus.publish('block_start', block_idx=block_idx, block_def=block_def)

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
            record = self.run_trial(trial_data, block_idx=block_idx,
                                    trial_idx=trial_idx, block_def=block_def)
            record['trial_idx_global'] = self._global_trial_idx
            self._global_trial_idx += 1
            self.data_writer.write_trial(record)
            self.event_bus.publish('trial_end', record=record)

        self.event_bus.publish('block_end', block_idx=block_idx, block_def=block_def)
        self.logger.log(f"Block {block_idx} | END")

    # ═════════════════════════════════════════════════════════════════
    # RUN
    # ═════════════════════════════════════════════════════════════════

    def run(self) -> Path | None:
        saved_path = None
        try:
            self.show_text_and_wait(self._get_instruction_text())
            self.wait_for_trigger()
            self.run_rest(label='initial')

            n = len(self.block_sequence)
            for i, bdef in enumerate(self.block_sequence):
                self.run_block(i, bdef)
                if i < n - 1:
                    self._run_inter_block(i)

            self.run_rest(label='final')
            self.logger.ok(f"Task {self.TASK_NAME} completed.")

        except AbortExperiment as e:
            self.logger.warn(f"ABORT: {e}")
        except (KeyboardInterrupt, SystemExit):
            self.logger.warn("Interrupted.")
        except Exception as e:
            self.logger.err(f"CRITICAL: {e}")
            import traceback
            traceback.print_exc()
        finally:
            saved_path = self._finish()
        return saved_path

    def _run_inter_block(self, block_idx):
        import random
        paradigm = self.design.get('paradigm', 'block')
        ib_min = self.design.get('inter_block_min', 0.0)
        ib_max = self.design.get('inter_block_max', 0.0)
        if paradigm == 'hybrid' and ib_max > 0:
            self.run_rest(label=f'jitter_{block_idx}',
                          duration=random.uniform(ib_min, ib_max))
        else:
            self.run_rest(label=f'after_block_{block_idx}')

    def _finish(self) -> Path | None:
        t = self.clock.time
        self.logger.log(f"Session end | t={t:.1f}s ({t/60:.1f} min)")

        try: self.hardware.send_trigger(TTL_END_EXP)
        except Exception: pass

        try: self.hardware.send_eyetracker_message(f"END_EXP_t{t:.3f}")
        except Exception: pass

        try:
            if self.hardware.has_eyetracker:
                self.hardware.stop_eyetracker()
                if self.hardware._eyetracker is not None:
                    self.hardware._eyetracker.transfer_data(
                        str(self.settings.task_dir(self.TASK_NAME))
                    )
        except Exception as e:
            self.logger.warn(f"ET cleanup: {e}")

        # Audio cleanup
        if self._audio is not None:
            try:
                self._audio.close()
            except Exception:
                pass

        saved = None
        if self.settings.save_data:
            try: saved = self.data_writer.save_final()
            except Exception as e: self.logger.err(f"Save failed: {e}")

        try: self.data_writer.close()
        except Exception: pass

        try:
            if self.data_writer.records:
                self._print_task_stats()
        except Exception: pass

        try:
            if self.win and not getattr(self.win, '_closed', False):
                self._instruction_stim.text = "Fin de la session.\nMerci."
                self._instruction_stim.draw()
                self.win.flip()
                self.clock.wait(END_SCREEN_DURATION)
        except Exception: pass

        self.event_bus.publish('task_end', saved_path=saved)
        return saved

    def _base_record(self, block_idx, trial_idx, block_def):
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