"""Pytest fixtures for the framework test suite."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from pathlib import Path

from config.settings import ExperimentSettings
from config.scanners.base import ScannerConfig
from core.clock import ExperimentClock
from core.events import EventBus
from dataio.logger import ExperimentLogger
from dataio.data_writer import DataWriter
from hardware.manager import HardwareManager


@pytest.fixture
def tmp_data_dir(tmp_path):
    return tmp_path / 'data'


@pytest.fixture
def settings(tmp_data_dir):
    return ExperimentSettings(
        participant_id='TEST01',
        session='01',
        scanner_name='pc',
        mode='pc',
        fullscreen=False,
        data_root=tmp_data_dir,
    )


@pytest.fixture
def scanner():
    return ScannerConfig(name='test')


@pytest.fixture
def logger(settings):
    return ExperimentLogger(settings)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_win():
    win = MagicMock()
    win._closed = False
    win.flip = MagicMock()
    return win


@pytest.fixture
def mock_clock():
    clock = MagicMock(spec=ExperimentClock)
    clock.time = 0.0
    clock.trigger_wall_time = '2025-01-01_00:00:00.000000'
    clock.psychopy_clock = MagicMock()
    return clock


@pytest.fixture
def mock_hardware(scanner, logger):
    hw = MagicMock(spec=HardwareManager)
    hw.has_trigger_output = False
    hw.has_eyetracker = False
    return hw


@pytest.fixture
def data_writer(tmp_data_dir, logger):
    return DataWriter(
        output_dir=tmp_data_dir / 'test_task',
        filename='test_events',
        logger=logger,
    )