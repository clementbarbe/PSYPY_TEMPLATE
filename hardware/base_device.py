"""
Abstract base class for all hardware devices.

Every device implements open / close / is_connected.
The HardwareManager interacts only through this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseDevice(ABC):
    """ABC for hardware peripherals."""

    @abstractmethod
    def open(self) -> bool:
        """Initialise connection. Return True on success."""

    @abstractmethod
    def close(self) -> None:
        """Release hardware resources."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if device is operational."""