"""Timing utilities for frame-accurate fMRI experiments."""

from __future__ import annotations


def seconds_to_frames(seconds: float, refresh_rate: float) -> int:
    """Convert duration in seconds to number of frames."""
    return max(1, round(seconds * refresh_rate))


def frames_to_seconds(frames: int, refresh_rate: float) -> float:
    """Convert frame count to seconds."""
    return frames / refresh_rate if refresh_rate > 0 else frames / 60.0


def snap_to_frame(duration: float, refresh_rate: float) -> float:
    """Snap a duration to the nearest whole frame boundary."""
    n_frames = round(duration * refresh_rate)
    return n_frames / refresh_rate


def estimate_run_duration(
    n_trials: int,
    stim_duration: float,
    mean_isi: float,
    n_blocks: int = 1,
    rest_duration: float = 10.0,
    instruction_duration: float = 3.0,
) -> float:
    """Estimate total run duration in seconds."""
    trial_time = n_trials * (stim_duration + mean_isi)
    rest_time = (n_blocks + 1) * rest_duration
    instr_time = n_blocks * instruction_duration
    return trial_time + rest_time + instr_time