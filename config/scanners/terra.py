"""TERRA scanner configuration."""

from config.scanners.base import ScannerConfig, TriggerInput, TriggerOutput


def TerraConfig() -> ScannerConfig:
    return ScannerConfig(
        name='terra',

        screen_width_px=1920,
        screen_height_px=1080,
        screen_width_cm=59.5,
        screen_height_cm=33.5,
        viewing_distance_cm=140.0,
        refresh_rate=60.0,

        flip_horizontal=True,
        flip_vertical=False,
        screen_index=1,

        trigger_input=TriggerInput.SERIAL,
        trigger_serial_port='COM3',
        trigger_serial_baud=115200,
        trigger_output=TriggerOutput.SERIAL,
        output_serial_port='COM4',
        output_serial_baud=115200,

        response_keys={
            'left': 'b',
            'right': 'y',
            'go': 'b',
        },
    )