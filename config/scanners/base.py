"""
Base scanner configuration dataclass.

Each scanner site overrides this with its own physical parameters.
The framework reads these to configure window, monitor, and hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from config.visual_params import compute_ppd


class TriggerInput(Enum):
    """How we RECEIVE the scanner sync pulse."""
    KEYBOARD = 'keyboard'
    SERIAL = 'serial'
    PARALLEL = 'parallel'


class TriggerOutput(Enum):
    """How we SEND event markers (TTL)."""
    PARALLEL = 'parallel'
    SERIAL = 'serial'
    NONE = 'none'


@dataclass
class ScannerConfig:
    """
    Physical and logical parameters for one scanner site.

    All visual calculations (degrees → pixels) derive from these values.
    Hardware initialization reads trigger_input / trigger_output.
    """

    # ── Identity ─────────────────────────────────────────────────────
    name: str = 'pc'

    # ── Screen geometry ──────────────────────────────────────────────
    screen_width_px: int = 1920
    screen_height_px: int = 1080
    screen_width_cm: float = 53.0
    screen_height_cm: float = 30.0
    viewing_distance_cm: float = 60.0
    refresh_rate: float = 60.0

    # ── Display transforms ───────────────────────────────────────────
    flip_horizontal: bool = False
    flip_vertical: bool = False
    screen_index: int = 0       # multi-monitor index

    # ── Trigger input (scanner → PC) ────────────────────────────────
    trigger_input: TriggerInput = TriggerInput.KEYBOARD
    trigger_key: str = 't'      # key sent by scanner (keyboard mode)
    trigger_serial_port: str = ''
    trigger_serial_baud: int = 115200

    # ── Trigger output (PC → recording) ─────────────────────────────
    trigger_output: TriggerOutput = TriggerOutput.NONE
    parallel_port_address: int = 0x0378
    output_serial_port: str = ''
    output_serial_baud: int = 115200

    # ── Response keys ────────────────────────────────────────────────
    response_keys: dict = field(default_factory=lambda: {
        'left': 'left',
        'right': 'right',
        'go': 'space',
    })

    # ── Computed properties ──────────────────────────────────────────
    @property
    def resolution(self) -> tuple[int, int]:
        return (self.screen_width_px, self.screen_height_px)

    @property
    def pixels_per_degree(self) -> float:
        return compute_ppd(
            self.screen_width_px,
            self.screen_width_cm,
            self.viewing_distance_cm,
        )

    @property
    def frame_duration(self) -> float:
        """Nominal frame duration in seconds."""
        return 1.0 / self.refresh_rate if self.refresh_rate > 0 else 1 / 60