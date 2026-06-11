"""Visual utilities — stimulus size helpers."""

from __future__ import annotations

from config.visual_params import dva_to_pixels, compute_ppd


def dva_to_norm(
    dva: float,
    screen_width_px: int,
    screen_width_cm: float,
    viewing_distance_cm: float,
) -> float:
    """Convert degrees of visual angle to PsychoPy norm units (width)."""
    ppd = compute_ppd(screen_width_px, screen_width_cm, viewing_distance_cm)
    px = dva_to_pixels(dva, ppd)
    return (px / screen_width_px) * 2.0  # norm goes from -1 to +1