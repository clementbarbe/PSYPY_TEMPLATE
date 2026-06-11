"""
HardwareManager — single façade for all hardware.

Tasks call:
    self.hardware.send_trigger(code)
    self.hardware.send_eyetracker_message(msg)
    self.hardware.emergency_shutdown(data_dir)

Cleanup is idempotent — safe to call close() multiple times.
"""

from __future__ import annotations

from pathlib import Path

from config.scanners.base import ScannerConfig, TriggerInput, TriggerOutput
from hardware.parallel_port import ParallelPort
from hardware.serial_trigger import SerialTrigger
from hardware.keyboard_trigger import KeyboardTrigger
from hardware.eyetracker import EyeTracker
from dataio.logger import ExperimentLogger


class HardwareManager:
    """Unified hardware interface with safe cleanup."""

    def __init__(
        self,
        scanner: ScannerConfig,
        logger: ExperimentLogger,
        enabled: bool = True,
    ):
        self._scanner = scanner
        self._logger = logger
        self._enabled = enabled
        self._closed = False

        self._trigger_output = None
        self._trigger_input = None
        self._eyetracker: EyeTracker | None = None

        if enabled:
            self._init_trigger_output()
        self._init_trigger_input()

    # ═════════════════════════════════════════════════════════════════
    # Initialisation
    # ═════════════════════════════════════════════════════════════════

    def _init_trigger_output(self) -> None:
        out = self._scanner.trigger_output
        if out == TriggerOutput.PARALLEL:
            dev = ParallelPort(
                address=self._scanner.parallel_port_address,
                logger=self._logger,
            )
            if dev.open():
                self._trigger_output = dev
        elif out == TriggerOutput.SERIAL:
            dev = SerialTrigger(
                port=self._scanner.output_serial_port,
                baudrate=self._scanner.output_serial_baud,
                logger=self._logger,
            )
            if dev.open():
                self._trigger_output = dev
        elif out == TriggerOutput.NONE:
            self._logger.log("Trigger output: NONE (disabled)")

    def _init_trigger_input(self) -> None:
        inp = self._scanner.trigger_input
        if inp == TriggerInput.SERIAL:
            dev = SerialTrigger(
                port=self._scanner.trigger_serial_port,
                baudrate=self._scanner.trigger_serial_baud,
                logger=self._logger,
            )
            if dev.open():
                self._trigger_input = dev
                return
        dev = KeyboardTrigger(
            trigger_key=self._scanner.trigger_key,
            logger=self._logger,
        )
        dev.open()
        self._trigger_input = dev

    def init_eyetracker(self) -> bool:
        """Initialise eye-tracker. Call separately if needed."""
        self._eyetracker = EyeTracker(logger=self._logger)
        return self._eyetracker.open()

    # ═════════════════════════════════════════════════════════════════
    # Public API — used by tasks
    # ═════════════════════════════════════════════════════════════════

    def send_trigger(self, code: int) -> None:
        if self._trigger_output is not None and not self._closed:
            self._trigger_output.send(code)

    def wait_for_scanner_trigger(self, timeout: float = 300.0) -> bool:
        if self._trigger_input is None:
            self._logger.warn("No trigger input device — skipping wait.")
            return True
        if isinstance(self._trigger_input, KeyboardTrigger):
            return self._trigger_input.wait(timeout)
        elif isinstance(self._trigger_input, SerialTrigger):
            return self._trigger_input.wait_byte(timeout=timeout)
        return False

    def send_eyetracker_message(self, msg: str) -> None:
        if self._eyetracker is not None:
            self._eyetracker.send_message(msg)

    def start_eyetracker(self, filename: str = 'et.edf') -> None:
        if self._eyetracker is not None:
            self._eyetracker.start_recording(filename)

    def stop_eyetracker(self) -> None:
        if self._eyetracker is not None:
            self._eyetracker.stop_recording()

    @property
    def has_trigger_output(self) -> bool:
        return self._trigger_output is not None

    @property
    def has_eyetracker(self) -> bool:
        return (self._eyetracker is not None
                and self._eyetracker.is_connected())

    # ═════════════════════════════════════════════════════════════════
    # Cleanup — IDEMPOTENT (safe to call multiple times)
    # ═════════════════════════════════════════════════════════════════

    def emergency_shutdown(self, data_dir: str | Path | None = None) -> None:
        """
        Emergency cleanup: save eyetracker data + close everything.

        Called on escape, CTRL+C, or unhandled exception.
        Safe to call multiple times.
        """
        if self._closed:
            return

        self._logger.warn("Emergency shutdown — closing all hardware")

        # 1. Eyetracker: transfer data BEFORE closing
        if self._eyetracker is not None:
            if data_dir is not None:
                try:
                    self._eyetracker.transfer_data(str(data_dir))
                except Exception as e:
                    self._logger.warn(f"ET emergency transfer: {e}")
            try:
                self._eyetracker.close()
            except Exception as e:
                self._logger.warn(f"ET emergency close: {e}")

        # 2. Reset trigger output (send 0)
        if self._trigger_output is not None:
            try:
                self._trigger_output.send(0)
            except Exception:
                pass

        # 3. Close everything
        self.close()

    def close(self) -> None:
        """Release all hardware resources. Idempotent."""
        if self._closed:
            return
        self._closed = True

        for dev in (self._trigger_output, self._trigger_input,
                    self._eyetracker):
            if dev is not None:
                try:
                    dev.close()
                except Exception:
                    pass

        self._logger.log("HardwareManager closed.")