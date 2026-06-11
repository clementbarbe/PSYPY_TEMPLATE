"""
Parallel port trigger device for TTL event markers.

Sends a byte value then resets to 0 after a short pulse.
Gracefully degrades if hardware is unavailable.
"""

from __future__ import annotations

import time
from hardware.base_device import BaseDevice

_PULSE_DURATION = 0.005  # 5 ms pulse width


class ParallelPort(BaseDevice):
    """Send TTL triggers via parallel port."""

    def __init__(self, address: int = 0x0378, logger=None):
        self._address = address
        self._port = None
        self._logger = logger

    def open(self) -> bool:
        try:
            from psychopy import parallel
            self._port = parallel.ParallelPort(address=self._address)
            self._port.setData(0)
            if self._logger:
                self._logger.ok(f"ParallelPort opened @ {hex(self._address)}")
            return True
        except Exception as e:
            if self._logger:
                self._logger.warn(
                    f"ParallelPort failed @ {hex(self._address)}: {e}"
                )
            self._port = None
            return False

    def close(self) -> None:
        if self._port is not None:
            try:
                self._port.setData(0)
            except Exception:
                pass
            self._port = None

    def is_connected(self) -> bool:
        return self._port is not None

    def send(self, code: int) -> None:
        """Send TTL pulse: set *code*, wait, reset to 0."""
        if self._port is None:
            return
        try:
            self._port.setData(int(code) & 0xFF)
            time.sleep(_PULSE_DURATION)
            self._port.setData(0)
        except Exception as e:
            if self._logger:
                self._logger.warn(f"ParallelPort send error: {e}")