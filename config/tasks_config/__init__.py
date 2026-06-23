"""
Task configuration loader.

Loads task-specific parameters from YAML files.
Falls back to built-in Python defaults if YAML unavailable.
"""

from __future__ import annotations

from pathlib import Path
from copy import deepcopy

_CONFIG_DIR = Path(__file__).parent


def load_task_config(task_name: str, config_dir: Path | None = None) -> dict:
    """
    Load task config from YAML, with built-in fallback.

    Args:
        task_name: e.g. 'flanker', 'nback'
        config_dir: override directory for YAML files

    Returns:
        dict with keys: task_name, designs, stimulus, responses, ttl_codes, ...
    """
    search_dir = config_dir or _CONFIG_DIR
    yaml_path = search_dir / f'{task_name}.yaml'

    if yaml_path.exists():
        try:
            import yaml
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            # Normalize design keys to int
            if 'designs' in config:
                config['designs'] = {
                    int(k): v for k, v in config['designs'].items()
                }
            return config
        except ImportError:
            pass   # PyYAML not installed — use fallback
        except Exception:
            pass   # Malformed YAML — use fallback

    # ── Fallback: built-in defaults ──────────────────────────────────
    return deepcopy(_BUILTIN_DEFAULTS.get(task_name, {}))


# ═════════════════════════════════════════════════════════════════════════════
# BUILT-IN DEFAULTS (used when YAML unavailable)
# ═════════════════════════════════════════════════════════════════════════════

_BUILTIN_DEFAULTS: dict[str, dict] = {
    'flanker': {
        'task_name': 'flanker',
        'display_name': 'Eriksen Flanker',
        'stimulus': {
            'arrow_height': 0.15,
            'arrow_font': 'monospace',
            'fixation_height': 0.1,
        },
        'ttl_codes': {
            'stim_congruent': 100,
            'stim_incongruent': 101,
            'stim_neutral': 102,
            'response_correct': 150,
            'response_incorrect': 151,
            'block_congruent': 10,
            'block_incongruent': 11,
            'block_mixed': 12,
            'block_neutral': 13,
        },
        'designs': {
            1: {
                'name': 'Block (CON vs INC ~7min)',
                'paradigm': 'block',
                'rest_duration': 12.0,
                'stim_duration': 1.5,
                'isi_min': 1.0,
                'isi_max': 1.0,
                'inter_block_min': 0.0,
                'inter_block_max': 0.0,
                'instruction_duration': 3.0,
                'pre_block_fixation': 1.0,
                'blocks': [
                    {'condition': 'congruent',   'n_trials': 20},
                    {'condition': 'incongruent', 'n_trials': 20},
                    {'condition': 'incongruent', 'n_trials': 20},
                    {'condition': 'congruent',   'n_trials': 20},
                    {'condition': 'incongruent', 'n_trials': 20},
                    {'condition': 'congruent',   'n_trials': 20},
                ],
            },
            2: {
                'name': 'Event-related (jittered ~9min)',
                'paradigm': 'event',
                'rest_duration': 15.0,
                'stim_duration': 1.5,
                'isi_min': 2.0,
                'isi_max': 6.0,
                'inter_block_min': 0.0,
                'inter_block_max': 0.0,
                'instruction_duration': 3.0,
                'pre_block_fixation': 1.0,
                'blocks': [
                    {'condition': 'mixed', 'n_trials': 96,
                     'prop_incongruent': 0.5},
                ],
            },
            3: {
                'name': 'Hybrid mini-blocks (~7min)',
                'paradigm': 'hybrid',
                'rest_duration': 12.0,
                'stim_duration': 1.5,
                'isi_min': 1.0,
                'isi_max': 2.0,
                'inter_block_min': 4.0,
                'inter_block_max': 10.0,
                'instruction_duration': 0.0,
                'pre_block_fixation': 0.0,
                'blocks': [
                    {'condition': 'mixed', 'n_trials': 8,
                     'prop_incongruent': 0.5}
                    for _ in range(12)
                ],
            },
            4: {
                'name': 'Hybrid optimisé (~7min)',
                'paradigm': 'hybrid',
                'rest_duration': 10.0,
                'stim_duration': 1.5,
                'isi_min': 1.0,
                'isi_max': 1.5,
                'inter_block_min': 3.0,
                'inter_block_max': 7.0,
                'instruction_duration': 0.0,
                'pre_block_fixation': 0.0,
                'blocks': [
                    {'condition': 'mixed', 'n_trials': 4,
                     'prop_incongruent': 0.5}
                    for _ in range(24)
                ],
            },
        },
    },

    'nback': {
        'task_name': 'nback',
        'display_name': 'N-Back',
        'stimulus': {
            'letter_height': 0.15,
            'cue_height': 0.20,
            'fixation_height': 0.1,
        },
        'ttl_codes': {
            'stim_target': 100,
            'stim_nontarget': 101,
            'response_hit': 150,
            'response_false_alarm': 151,
        },
        'designs': {
            1: {
                'name': '0 vs 2-back (standard ~8min)',
                'rest_duration': 12.0,
                'stim_duration': 0.5,
                'isi_duration': 2.0,
                'instruction_duration': 4.0,
                'pre_block_fixation': 2.0,
                'target_ratio': 0.33,
                'blocks': [
                    {'level': 0, 'n_trials': 25},
                    {'level': 2, 'n_trials': 25},
                    {'level': 2, 'n_trials': 25},
                    {'level': 0, 'n_trials': 25},
                    {'level': 2, 'n_trials': 25},
                    {'level': 0, 'n_trials': 25},
                ],
            },
            2: {
                'name': '0 vs 2-back (dense)',
                'rest_duration': 10.0,
                'stim_duration': 0.5,
                'isi_duration': 2.0,
                'instruction_duration': 4.0,
                'pre_block_fixation': 2.0,
                'target_ratio': 0.33,
                'blocks': [
                    {'level': 0, 'n_trials': 20},
                    {'level': 2, 'n_trials': 20},
                    {'level': 2, 'n_trials': 20},
                    {'level': 0, 'n_trials': 20},
                    {'level': 2, 'n_trials': 20},
                    {'level': 0, 'n_trials': 20},
                ],
            },
            3: {
                'name': '1-2-3-back (paramétrique)',
                'rest_duration': 12.0,
                'stim_duration': 0.5,
                'isi_duration': 2.0,
                'instruction_duration': 4.0,
                'pre_block_fixation': 2.0,
                'target_ratio': 0.33,
                'blocks': [
                    {'level': 1, 'n_trials': 25},
                    {'level': 2, 'n_trials': 25},
                    {'level': 3, 'n_trials': 25},
                    {'level': 2, 'n_trials': 25},
                    {'level': 1, 'n_trials': 25},
                    {'level': 3, 'n_trials': 25},
                ],
            },
            4: {
                'name': '1-2-3-back (randomisé)',
                'rest_duration': 10.0,
                'stim_duration': 0.5,
                'isi_duration': 2.0,
                'instruction_duration': 4.0,
                'pre_block_fixation': 2.0,
                'target_ratio': 0.33,
                'blocks': [
                    {'level': 2, 'n_trials': 20},
                    {'level': 1, 'n_trials': 20},
                    {'level': 3, 'n_trials': 20},
                    {'level': 2, 'n_trials': 20},
                    {'level': 3, 'n_trials': 20},
                    {'level': 1, 'n_trials': 20},
                ],
            },
        },
    },

    'stroop': {
        'task_name': 'stroop',
        'display_name': 'Stroop',
        'stimulus': {'word_height': 0.15, 'fixation_height': 0.1},
        'colors': {
            'rouge': [1.0, -1.0, -1.0],
            'orange': [1.0, 0.3, -1.0],
            'vert': [-1.0, 0.8, -1.0],
        },
        'color_words': {'rouge': 'ROUGE', 'orange': 'ORANGE', 'vert': 'VERT'},
        'neutral_words': {
            'rouge': ['TABLE', 'PORTE', 'LIVRE', 'CHAMP', 'PLAGE'],
            'vert': ['PONT', 'BRAS', 'LOUP', 'TOIT', 'MURS'],
            'orange': ['JARDIN', 'BATEAU', 'PIERRE', 'MARCHE', 'FEUTRE'],
        },
        'response_keys_pc': {'rouge': 'left', 'orange': 'down', 'vert': 'right'},
        'response_keys_fmri': {'rouge': 'b', 'orange': 'y', 'vert': 'g'},
        'ttl_codes': {
            'stim_congruent': 110, 'stim_incongruent': 111, 'stim_neutral': 112,
            'response_correct': 160, 'response_incorrect': 161,
            'block_neutral': 20, 'block_incongruent': 21, 'block_congruent': 22,
        },
        'designs': {
            1: {
                'name': 'Bloc Ordre A (N-I-N-C x4)',
                'paradigm': 'block',
                'fixation_duration': 0.3, 'stim_duration': 1.2,
                'iti_duration': 0.5, 'rest_duration': 10.0,
                'instruction_duration': 3.0, 'pre_block_fixation': 1.0,
                'prop_neutral_mix': 0.5,
                'blocks': [
                    {'condition': 'neutral', 'n_trials': 18},
                    {'condition': 'incongruent', 'n_trials': 18},
                    {'condition': 'neutral', 'n_trials': 18},
                    {'condition': 'congruent', 'n_trials': 18},
                ] * 4,
            },
            2: {
                'name': 'Bloc Ordre B (N-C-N-I x4)',
                'paradigm': 'block',
                'fixation_duration': 0.3, 'stim_duration': 1.2,
                'iti_duration': 0.5, 'rest_duration': 10.0,
                'instruction_duration': 3.0, 'pre_block_fixation': 1.0,
                'prop_neutral_mix': 0.5,
                'blocks': [
                    {'condition': 'neutral', 'n_trials': 18},
                    {'condition': 'congruent', 'n_trials': 18},
                    {'condition': 'neutral', 'n_trials': 18},
                    {'condition': 'incongruent', 'n_trials': 18},
                ] * 4,
            },
            3: {
                'name': 'Bloc court (N-I-N-C x2)',
                'paradigm': 'block',
                'fixation_duration': 0.3, 'stim_duration': 1.2,
                'iti_duration': 0.5, 'rest_duration': 10.0,
                'instruction_duration': 3.0, 'pre_block_fixation': 1.0,
                'prop_neutral_mix': 0.5,
                'blocks': [
                    {'condition': 'neutral', 'n_trials': 18},
                    {'condition': 'incongruent', 'n_trials': 18},
                    {'condition': 'neutral', 'n_trials': 18},
                    {'condition': 'congruent', 'n_trials': 18},
                ] * 2,
            },
            4: {
                'name': 'Event-related mixte',
                'paradigm': 'event',
                'fixation_duration': 0.3, 'stim_duration': 1.2,
                'iti_duration': 0.5, 'rest_duration': 12.0,
                'instruction_duration': 3.0, 'pre_block_fixation': 1.0,
                'prop_neutral_mix': 0.0,
                'blocks': [
                    {'condition': 'mixed', 'n_trials': 120,
                     'prop_congruent': 0.33, 'prop_incongruent': 0.33},
                ],
            },
        },
    },
}