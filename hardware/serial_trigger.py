"""
Serial port trigger device.

Used both for receiving scanner triggers and sending event markers,
depending on the scanner configuration.
"""

from __future__ import annotations

from hardware.base_device import BaseDevice


class SerialTrigger(BaseDevice):
    """Serial port trigger I/O."""

    def __init__(self, port: str, baudrate: int = 115200, logger=None):
        self._port_name = port
        self._baudrate = baudrate
        self._serial = None
        self._logger = logger

    def open(self) -> bool:
        try:
            import serial
            self._serial = serial.Serial(
                port=self._port_name,
                baudrate=self._baudrate,
                timeout=0.001,
            )
            if self._logger:
                self._logger.ok(
                    f"SerialTrigger opened: {self._port_name} "
                    f"@ {self._baudrate}"
                )
            return True
        except Exception as e:
            if self._logger:
                self._logger.warn(f"SerialTrigger failed: {e}")
            self._serial = None
            return False

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def send(self, code: int) -> None:
        """Send one byte."""
        if self._serial is None:
            return
        try:
            self._serial.write(bytes([int(code) & 0xFF]))
        except Exception as e:
            if self._logger:
                self._logger.warn(f"SerialTrigger send: {e}")

    def read_byte(self) -> int | None:
        """Non-blocking read of one byte. Return int or None."""
        if self._serial is None:
            return None
        try:
            if self._serial.in_waiting > 0:
                return self._serial.read(1)[0]
        except Exception:
            pass
        return None

    def wait_byte(self, target: int | None = None,
                  timeout: float = 300.0) -> bool:
        """Block until a byte is received (optionally matching *target*)."""
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            b = self.read_byte()
            if b is not None:
                if target is None or b == target:
                    return True
            time.sleep(0.0005)
        return False