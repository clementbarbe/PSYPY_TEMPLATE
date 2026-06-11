"""
Experiment-wide constants.
Nothing is hardcoded in task files.
"""

from pathlib import Path

# ── Project paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
STIMULI_DIR = PROJECT_ROOT / 'stimuli'
CONFIG_DIR = PROJECT_ROOT / 'config'

# ── Display ──────────────────────────────────────────────────────────────────
BG_COLOR = (-1, -1, -1)
TEXT_COLOR = (1, 1, 1)
FIXATION_COLOR = (1, 1, 1)
INSTRUCTION_COLOR = (1, 1, 0)
CUE_COLOR = (0, 1, 1)

# ── Typography ───────────────────────────────────────────────────────────────
DEFAULT_FONT = 'monospace'
FIXATION_HEIGHT = 0.1
INSTRUCTION_HEIGHT = 0.06
STIMULUS_HEIGHT = 0.15

# ── Timing ───────────────────────────────────────────────────────────────────
FRAME_TOLERANCE_SEC = 0.002
END_SCREEN_DURATION = 3.0
TRIGGER_TIMEOUT = 300.0

# ── Quit / Emergency ────────────────────────────────────────────────────────
QUIT_KEY = 'escape'

# ── Data ─────────────────────────────────────────────────────────────────────
TIMESTAMP_FMT = '%Y-%m-%d_%H-%M-%S'
TIMESTAMP_PRECISE_FMT = '%H:%M:%S.%f'
FILENAME_TEMPLATE = 'sub-{pid}_ses-{ses}_task-{task}_run-{run}'

# ── TTL defaults ─────────────────────────────────────────────────────────────
TTL_START_EXP = 255
TTL_END_EXP = 254
TTL_REST_START = 200
TTL_REST_END = 201
TTL_INSTRUCTION = 210