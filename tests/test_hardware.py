"""Tests for hardware abstractions."""

import pytest
from unittest.mock import MagicMock

from config.scanners.base import ScannerConfig, TriggerOutput
from hardware.manager import HardwareManager


class TestHardwareManager:
    def test_send_trigger_no_device(self, scanner, logger):
        """send_trigger should not raise when no device."""
        hw = HardwareManager(scanner, logger, enabled=False)
        hw.send_trigger(100)  # should not raise

    def test_eyetracker_message_no_device(self, scanner, logger):
        hw = HardwareManager(scanner, logger, enabled=False)
        hw.send_eyetracker_message("test")  # should not raise