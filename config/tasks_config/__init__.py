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
                'name': 'Compact 0v2 (~6min)',
                'rest_duration': 6.0,
                'stim_duration': 0.5,
                'isi_duration': 1.5,
                'instruction_duration': 4.0,
                'pre_block_fixation': 0.0,
                'target_ratio': 0.30,
                'blocks': [
                    {'level': l, 'n_trials': 12}
                    for l in [0, 2] * 4
                ],
            },
            2: {
                'name': 'Balanced 0v2 (~7min)',
                'rest_duration': 7.0,
                'stim_duration': 0.5,
                'isi_duration': 1.5,
                'instruction_duration': 4.0,
                'pre_block_fixation': 0.0,
                'target_ratio': 0.30,
                'blocks': [
                    {'level': l, 'n_trials': 12}
                    for l in [0, 2] * 5
                ],
            },
            3: {
                'name': 'Power 0v2 (~8min30)',
                'rest_duration': 8.0,
                'stim_duration': 0.5,
                'isi_duration': 1.5,
                'instruction_duration': 4.0,
                'pre_block_fixation': 0.0,
                'target_ratio': 0.30,
                'blocks': [
                    {'level': l, 'n_trials': 14}
                    for l in [0, 2] * 6
                ],
            },
            4: {
                'name': 'Research 0v2 (~10min)',
                'rest_duration': 10.0,
                'stim_duration': 0.5,
                'isi_duration': 1.5,
                'instruction_duration': 4.0,
                'pre_block_fixation': 0.0,
                'target_ratio': 0.30,
                'blocks': [
                    {'level': l, 'n_trials': 15}
                    for l in [0, 2] * 7
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
            'bleu': [-1.0, -1.0, 1.0],
            'vert': [-1.0, 0.8, -1.0],
        },
        'color_words': {'rouge': 'ROUGE', 'bleu': 'BLEU', 'vert': 'VERT'},
        'neutral_words': ['XXXX', '%%%%', 'OOOO'],
        'incongruent_pairs': [
            {'word': 'ROUGE', 'ink': 'bleu'}, {'word': 'ROUGE', 'ink': 'vert'},
            {'word': 'BLEU', 'ink': 'rouge'}, {'word': 'BLEU', 'ink': 'vert'},
            {'word': 'VERT', 'ink': 'rouge'}, {'word': 'VERT', 'ink': 'bleu'},
        ],
        'response_keys_pc': {'rouge': 'left', 'bleu': 'down', 'vert': 'right'},
        'response_keys_fmri': {'rouge': 'b', 'bleu': 'y', 'vert': 'g'},
        'show_key_reminder': True,
        'key_reminder_height': 0.04,
        'key_reminder_y': -0.85,
        'ttl_codes': {
            'stim_congruent': 110, 'stim_incongruent': 111, 'stim_neutral': 112,
            'response_correct': 160, 'response_incorrect': 161,
            'block_neutral': 20, 'block_incongruent': 21, 'block_congruent': 22,
        },
        'designs': {
            1: {
                'name': 'Initial 15x10 (~7min20)',
                'paradigm': 'block',
                'fixation_duration': 0.5, 'stim_duration': 1.2,
                'iti_duration': 0.3, 'rest_duration': 10.0,
                'instruction_duration': 3.0, 'pre_block_fixation': 0.0,
                'blocks': [
                    {'condition': c, 'n_trials': 10}
                    for c in ['neutral', 'congruent', 'incongruent'] * 5
                ],
            },
            2: {
                'name': 'Optimise 15x8 (~5min50)',
                'paradigm': 'block',
                'fixation_duration': 0.5, 'stim_duration': 1.2,
                'iti_duration': 0.3, 'rest_duration': 8.0,
                'instruction_duration': 3.0, 'pre_block_fixation': 0.0,
                'blocks': [
                    {'condition': c, 'n_trials': 8}
                    for c in ['neutral', 'congruent', 'incongruent'] * 5
                ],
            },
            3: {
                'name': 'Compact 12x10 (~5min30)',
                'paradigm': 'block',
                'fixation_duration': 0.5, 'stim_duration': 1.2,
                'iti_duration': 0.3, 'rest_duration': 8.0,
                'instruction_duration': 3.0, 'pre_block_fixation': 0.0,
                'blocks': [
                    {'condition': c, 'n_trials': 10}
                    for c in ['neutral', 'congruent', 'incongruent'] * 4
                ],
            },
            4: {
                'name': 'Final 9x15 (~5min25)',
                'paradigm': 'block',
                'fixation_duration': 0.5, 'stim_duration': 1.2,
                'iti_duration': 0.3, 'rest_duration': 7.0,
                'instruction_duration': 3.0, 'pre_block_fixation': 0.0,
                'blocks': [
                    {'condition': c, 'n_trials': 15}
                    for c in ['neutral', 'congruent', 'incongruent'] * 3
                ],
            },
        },
    },
    
    'oddball': {
        'task_name': 'oddball',
        'display_name': 'Oddball Auditif',
        'stimulus': {'fixation_height': 0.1},
        'audio': {
            'standard_freq': 1000,
            'deviant_freq': 1200,
            'tone_duration': 0.2,
            'tone_volume': 0.8,
        },
        'ttl_codes': {
            'stim_standard': 120, 'stim_deviant': 121,
            'response_hit': 170, 'response_fa': 171,
        },
        'designs': {
            1: {
                'name': 'Standard 80/20 (~8min)',
                'paradigm': 'block',
                'rest_duration': 12.0,
                'instruction_duration': 3.0,
                'pre_block_fixation': 1.0,
                'soa_min': 1.2, 'soa_max': 1.8,
                'prop_deviant': 0.20,
                'blocks': [
                    {'n_trials': 80},
                    {'n_trials': 80},
                    {'n_trials': 80},
                ],
            },
            2: {
                'name': 'Dense 80/20 (~5min)',
                'paradigm': 'block',
                'rest_duration': 10.0,
                'instruction_duration': 3.0,
                'pre_block_fixation': 1.0,
                'soa_min': 1.0, 'soa_max': 1.5,
                'prop_deviant': 0.20,
                'blocks': [
                    {'n_trials': 100},
                    {'n_trials': 100},
                ],
            },
            3: {
                'name': 'Court 80/20 (~3min)',
                'paradigm': 'block',
                'rest_duration': 8.0,
                'instruction_duration': 3.0,
                'pre_block_fixation': 1.0,
                'soa_min': 1.2, 'soa_max': 1.8,
                'prop_deviant': 0.20,
                'blocks': [{'n_trials': 80}],
            },
            4: {
                'name': '70/30 plus de deviants (~7min)',
                'paradigm': 'block',
                'rest_duration': 10.0,
                'instruction_duration': 3.0,
                'pre_block_fixation': 1.0,
                'soa_min': 1.2, 'soa_max': 1.8,
                'prop_deviant': 0.30,
                'blocks': [
                    {'n_trials': 80},
                    {'n_trials': 80},
                ],
            },
        },
    },
}