"""
Base scanner configuration.
PC mode uses arrow keys by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from config.visual_params import compute_ppd


class TriggerInput(Enum):
    KEYBOARD = 'keyboard'
    SERIAL = 'serial'
    PARALLEL = 'parallel'


class TriggerOutput(Enum):
    PARALLEL = 'parallel'
    SERIAL = 'serial'
    NONE = 'none'


@dataclass
class ScannerConfig:
    """Physical and logical parameters for one scanner site."""

    name: str = 'pc'

    screen_width_px: int = 1920
    screen_height_px: int = 1080
    screen_width_cm: float = 53.0
    screen_height_cm: float = 30.0
    viewing_distance_cm: float = 60.0
    refresh_rate: float = 60.0

    flip_horizontal: bool = False
    flip_vertical: bool = False
    screen_index: int = 0

    trigger_input: TriggerInput = TriggerInput.KEYBOARD
    trigger_key: str = 't'
    trigger_serial_port: str = ''
    trigger_serial_baud: int = 115200

    trigger_output: TriggerOutput = TriggerOutput.NONE
    parallel_port_address: int = 0x0378
    output_serial_port: str = ''
    output_serial_baud: int = 115200

    # ── Response keys — arrow keys for PC ────────────────────────────
    response_keys: dict = field(default_factory=lambda: {
        'left': 'left',       # left arrow
        'right': 'right',     # right arrow
        'go': 'space',
    })

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
        return 1.0 / self.refresh_rate if self.refresh_rate > 0 else 1 / 60