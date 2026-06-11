"""CIMA scanner configuration."""

from config.scanners.base import ScannerConfig, TriggerInput, TriggerOutput


def CimaConfig() -> ScannerConfig:
    return ScannerConfig(
        name='cima',

        # Screen
        screen_width_px=1920,
        screen_height_px=1080,
        screen_width_cm=69.8,
        screen_height_cm=39.3,
        viewing_distance_cm=156.0,
        refresh_rate=60.0,

        # Display
        flip_horizontal=False,
        flip_vertical=False,
        screen_index=1,

        # Triggers
        trigger_input=TriggerInput.KEYBOARD,
        trigger_key='t',
        trigger_output=TriggerOutput.PARALLEL,
        parallel_port_address=0xCFF8,

        # Response keys (fMRI button box)
        response_keys={
            'left': 'b',
            'right': 'y',
            'go': 'b',
        },
    )