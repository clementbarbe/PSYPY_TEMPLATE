"""PRISMA scanner configuration."""

from config.scanners.base import ScannerConfig, TriggerInput, TriggerOutput


def PrismaConfig() -> ScannerConfig:
    return ScannerConfig(
        name='prisma',

        screen_width_px=1024,
        screen_height_px=768,
        screen_width_cm=41.0,
        screen_height_cm=30.7,
        viewing_distance_cm=113.0,
        refresh_rate=60.0,

        flip_horizontal=False,
        flip_vertical=True,
        screen_index=0,

        trigger_input=TriggerInput.KEYBOARD,
        trigger_key='5',
        trigger_output=TriggerOutput.PARALLEL,
        parallel_port_address=0x0378,

        response_keys={
            'left': '1',
            'right': '4',
            'go': '1',
        },
    )