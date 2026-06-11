"""
Visual parameter conversions for multi-scanner support.

All visual stimuli should be defined in degrees of visual angle (DVA)
or screen proportions, then converted to pixels at runtime.
"""

from __future__ import annotations

import math


def cm_to_dva(size_cm: float, viewing_distance_cm: float) -> float:
    """Convert size in centimeters to degrees of visual angle."""
    return 2.0 * math.degrees(math.atan(size_cm / (2.0 * viewing_distance_cm)))


def dva_to_cm(dva: float, viewing_distance_cm: float) -> float:
    """Convert degrees of visual angle to centimeters."""
    return 2.0 * viewing_distance_cm * math.tan(math.radians(dva / 2.0))


def compute_ppd(
    screen_width_px: int,
    screen_width_cm: float,
    viewing_distance_cm: float,
) -> float:
    """Compute pixels per degree of visual angle."""
    total_dva = cm_to_dva(screen_width_cm, viewing_distance_cm)
    return screen_width_px / total_dva if total_dva > 0 else 1.0


def dva_to_pixels(dva: float, ppd: float) -> float:
    """Convert degrees of visual angle to pixels."""
    return dva * ppd


def pixels_to_dva(pixels: float, ppd: float) -> float:
    """Convert pixels to degrees of visual angle."""
    return pixels / ppd if ppd > 0 else 0.0