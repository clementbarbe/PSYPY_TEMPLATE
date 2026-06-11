"""
Custom exception hierarchy.

All framework exceptions inherit from FrameworkError.
AbortExperiment is raised on escape/CTRL+C for clean shutdown.
"""


class FrameworkError(Exception):
    """Base exception for all framework errors."""


class ConfigError(FrameworkError):
    """Invalid or missing configuration."""


class HardwareError(FrameworkError):
    """Hardware initialisation or communication failure."""


class TriggerError(FrameworkError):
    """Trigger timeout or invalid trigger."""


class TaskError(FrameworkError):
    """Error in task logic or setup."""


class TimingError(FrameworkError):
    """Timing violation (dropped frames, missed deadlines)."""


class DataError(FrameworkError):
    """Data saving or file I/O error."""


class AbortExperiment(FrameworkError):
    """
    Raised to cleanly abort the experiment.

    Triggers the full cleanup chain:
        1. Save incremental data
        2. Stop eyetracker recording
        3. Transfer eyetracker data
        4. Close hardware
        5. Close PsychoPy window
    """