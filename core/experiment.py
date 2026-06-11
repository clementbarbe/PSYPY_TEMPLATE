"""
Experiment — top-level orchestrator.

Creates PsychoPy window, clock, hardware, logger.
Registers atexit handler for emergency cleanup.
"""

from __future__ import annotations

import atexit
import signal
import sys
from pathlib import Path

from psychopy import visual, monitors

from config.settings import ExperimentSettings
from config.scanners import get_scanner
from config.scanners.base import ScannerConfig
from config.tasks_config import load_task_config
from config.constants import BG_COLOR
from core.clock import ExperimentClock
from core.events import EventBus
from core.exceptions import ConfigError
from hardware.manager import HardwareManager
from dataio.logger import ExperimentLogger
from dataio.data_writer import DataWriter
from tasks.registry import get_task


class Experiment:
    """
    Session-level container.

    Registers atexit + signal handlers so that hardware is always
    cleaned up, even on unhandled exceptions or force-quit.
    """

    # Class-level reference so atexit can find the active instance
    _active_instance: Experiment | None = None

    def __init__(self, settings: ExperimentSettings):
        self.settings = settings
        self.scanner: ScannerConfig = get_scanner(settings.scanner_name)
        self.event_bus = EventBus()

        self.logger = ExperimentLogger(settings)
        self.clock = ExperimentClock()
        self.win = self._create_window()
        self.hardware = HardwareManager(
            scanner=self.scanner,
            logger=self.logger,
            enabled=settings.trigger_output_enabled,
        )

        # ── Eyetracker init if enabled ───────────────────────────────
        if settings.eyetracker_enabled:
            self.hardware.init_eyetracker()

        # ── Safety net: atexit + signal handlers ─────────────────────
        Experiment._active_instance = self
        atexit.register(Experiment._atexit_cleanup)
        self._install_signal_handlers()

        self.logger.ok(
            f"Experiment initialised | scanner={self.scanner.name} | "
            f"mode={settings.mode} | resolution={self.scanner.resolution}"
        )

    # ═════════════════════════════════════════════════════════════════
    # Window
    # ═════════════════════════════════════════════════════════════════

    def _create_window(self) -> visual.Window:
        mon = monitors.Monitor(
            name=self.scanner.name,
            width=self.scanner.screen_width_cm,
            distance=self.scanner.viewing_distance_cm,
        )
        mon.setSizePix(list(self.scanner.resolution))

        win = visual.Window(
            size=self.scanner.resolution,
            fullscr=self.settings.fullscreen,
            monitor=mon,
            screen=self.scanner.screen_index,
            color=BG_COLOR,
            colorSpace='rgb',
            units='norm',
            allowGUI=False,
            waitBlanking=True,
        )

        if self.scanner.flip_horizontal or self.scanner.flip_vertical:
            flip_h = -1.0 if self.scanner.flip_horizontal else 1.0
            flip_v = -1.0 if self.scanner.flip_vertical else 1.0
            win.viewScale = [flip_h, flip_v]

        self.logger.log(
            f"Window created: {self.scanner.resolution} "
            f"@ {self.scanner.refresh_rate}Hz"
        )
        return win

    # ═════════════════════════════════════════════════════════════════
    # Task execution
    # ═════════════════════════════════════════════════════════════════

    def run_task(self, task_name: str, design_id: int = 1,
                 **kwargs) -> Path | None:
        task_cls = get_task(task_name)
        if task_cls is None:
            raise ConfigError(
                f"Unknown task '{task_name}'. "
                f"Register it with @register_task."
            )

        task_config = load_task_config(task_name)
        if not task_config:
            raise ConfigError(f"No config found for task '{task_name}'.")

        data_writer = DataWriter(
            output_dir=self.settings.task_dir(task_name),
            filename=self.settings.output_filename(task_name, 'events'),
            logger=self.logger,
        )

        task = task_cls(
            win=self.win,
            clock=self.clock,
            hardware=self.hardware,
            data_writer=data_writer,
            logger=self.logger,
            event_bus=self.event_bus,
            settings=self.settings,
            scanner=self.scanner,
            task_config=task_config,
            design_id=design_id,
            **kwargs,
        )

        self.logger.ok(f"Running task: {task_name} (design {design_id})")
        return task.run()

    # ═════════════════════════════════════════════════════════════════
    # Cleanup — idempotent
    # ═════════════════════════════════════════════════════════════════

    def cleanup(self) -> None:
        """Release all resources. Safe to call multiple times."""
        try:
            self.hardware.close()
        except Exception as e:
            self.logger.warn(f"Hardware cleanup: {e}")

        try:
            if self.win and not getattr(self.win, '_closed', True):
                self.win.close()
        except Exception:
            pass

        try:
            self.logger.ok("Experiment cleanup complete.")
            self.logger.close()
        except Exception:
            pass

        Experiment._active_instance = None

    # ═════════════════════════════════════════════════════════════════
    # Safety nets
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _atexit_cleanup():
        """Called by atexit — last resort cleanup."""
        inst = Experiment._active_instance
        if inst is not None:
            try:
                inst.hardware.emergency_shutdown(
                    data_dir=inst.settings.subject_dir
                )
            except Exception:
                pass
            try:
                if inst.win and not getattr(inst.win, '_closed', True):
                    inst.win.close()
            except Exception:
                pass

    def _install_signal_handlers(self) -> None:
        """Install signal handlers for CTRL+C (works on Windows + Linux)."""
        def handler(signum, frame):
            self.logger.warn(f"Signal {signum} received — emergency shutdown")
            self.hardware.emergency_shutdown(
                data_dir=self.settings.subject_dir
            )
            try:
                if self.win and not getattr(self.win, '_closed', True):
                    self.win.close()
            except Exception:
                pass
            sys.exit(1)

        try:
            signal.signal(signal.SIGINT, handler)
            # SIGTERM not available on Windows
            if hasattr(signal, 'SIGTERM'):
                signal.signal(signal.SIGTERM, handler)
        except Exception:
            pass  # Can't set signal in some contexts (e.g. threads)