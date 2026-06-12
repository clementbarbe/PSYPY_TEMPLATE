"""
Experiment-wide constants.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
STIMULI_DIR = PROJECT_ROOT / 'stimuli'
CONFIG_DIR = PROJECT_ROOT / 'config'

BG_COLOR = (-1, -1, -1)
TEXT_COLOR = (1, 1, 1)
FIXATION_COLOR = (1, 1, 1)
INSTRUCTION_COLOR = (1, 1, 0)
CUE_COLOR = (0, 1, 1)

DEFAULT_FONT = 'monospace'
FIXATION_HEIGHT = 0.1
INSTRUCTION_HEIGHT = 0.06
STIMULUS_HEIGHT = 0.15

FRAME_TOLERANCE_SEC = 0.002
END_SCREEN_DURATION = 3.0
TRIGGER_TIMEOUT = 300.0
QUIT_KEY = 'escape'

TIMESTAMP_FMT = '%Y-%m-%d_%H-%M-%S'
TIMESTAMP_PRECISE_FMT = '%H:%M:%S.%f'

TTL_START_EXP = 255
TTL_END_EXP = 254
TTL_REST_START = 200
TTL_REST_END = 201
TTL_INSTRUCTION = 210

# ── Audio ────────────────────────────────────────────────────────────
AUDIO_BACKEND = 'ptb'
AUDIO_SAMPLE_RATE = 48000
AUDIO_SCHEDULE_LEAD = 0.100     # schedule 100ms before target
AUDIO_MIN_LEAD = 0.030          # minimum 30ms or play immediately