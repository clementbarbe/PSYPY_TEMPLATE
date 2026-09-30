"""Moteur commun du framework fMRI."""

from core.config import SessionSettings
from core.design import DesignGenerator, GeneratedDesign
from core.errors import AbortExperiment, DesignError, TaskConfigurationError

__all__ = [
    "AbortExperiment",
    "DesignError",
    "DesignGenerator",
    "GeneratedDesign",
    "SessionSettings",
    "TaskConfigurationError",
]
