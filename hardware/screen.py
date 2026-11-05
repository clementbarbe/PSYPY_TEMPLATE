"""Création centralisée de la fenêtre de stimulation PsychoPy."""

from __future__ import annotations

from typing import Any

def create_psychopy_window(settings: Any) -> Any:
    """Crée la fenêtre PsychoPy à partir des paramètres écran validés."""
    from psychopy import monitors, visual

    monitor = monitors.Monitor(
        name="experiment_monitor",
        width=settings.width_cm,
        distance=settings.viewing_distance_cm,
    )
    monitor.setSizePix(list(settings.resolution))
    win = visual.Window(
        size=settings.resolution,
        fullscr=settings.fullscreen,
        screen=settings.screen_index,
        monitor=monitor,
        color=settings.background_color,
        colorSpace="rgb",
        units="norm",
        allowGUI=False,
        waitBlanking=True,
    )
    try:
        win.mouseVisible = False
    except Exception:
        pass
    if settings.flip_horizontal or settings.flip_vertical:
        win.viewScale = [
            -1.0 if settings.flip_horizontal else 1.0,
            -1.0 if settings.flip_vertical else 1.0,
        ]
    try:
        win.measured_refresh_rate = win.getActualFrameRate(nIdentical=20, nMaxFrames=240, nWarmUpFrames=30)
        if settings.trigger_enabled and not settings.mock_mode:
            measured = win.measured_refresh_rate
            if measured is None or abs(measured - settings.refresh_rate) > settings.refresh_rate * 0.03:
                raise RuntimeError(
                    f"Fréquence écran mesurée {measured!r} Hz ; attendue {settings.refresh_rate} Hz. "
                    "Vérifier l'écran choisi et le profil du poste."
                )
        win.refreshThreshold = 1.5 / (win.measured_refresh_rate or settings.refresh_rate)
    except BaseException:
        win.close()
        raise
    return win
