"""
Keyboard-based trigger — used when scanner sends a key-press
or for PC-mode manual trigger.
"""

from __future__ import annotations

from hardware.base_device import BaseDevice


class KeyboardTrigger(BaseDevice):
    """Keyboard trigger input (always available)."""

    def __init__(self, trigger_key: str = 't', logger=None):
        self.trigger_key = trigger_key
        self._keyboard = None
        self._logger = logger

    def open(self) -> bool:
        from psychopy.hardware import keyboard
        self._keyboard = keyboard.Keyboard()
        if self._logger:
            self._logger.log(f"KeyboardTrigger ready (key='{self.trigger_key}')")
        return True

    def close(self) -> None:
        self._keyboard = None

    def is_connected(self) -> bool:
        return self._keyboard is not None

    def wait(self, timeout: float = 300.0) -> bool:
        """Block until trigger key is pressed. Return True on success."""
        if self._keyboard is None:
            return False
        keys = self._keyboard.waitKeys(
            keyList=[self.trigger_key],
            maxWait=timeout,
        )
        return keys is not None and len(keys) > 0