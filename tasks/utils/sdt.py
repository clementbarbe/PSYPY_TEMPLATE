"""
Signal Detection Theory (SDT) classification.

Used by Go/No-Go tasks (N-back, etc.) to categorise
responses into Hit, Miss, False Alarm, Correct Rejection.
"""

from __future__ import annotations


def classify_sdt(is_target: bool, responded: bool) -> dict:
    """
    Classify a single trial using SDT.

    Args:
        is_target: whether this trial required a response (signal present)
        responded: whether the participant pressed the button

    Returns:
        dict with keys: hit, miss, false_alarm, correct_rejection, is_correct
    """
    if is_target:
        return {
            'hit': int(responded),
            'miss': int(not responded),
            'false_alarm': 0,
            'correct_rejection': 0,
            'is_correct': int(responded),
        }
    else:
        return {
            'hit': 0,
            'miss': 0,
            'false_alarm': int(responded),
            'correct_rejection': int(not responded),
            'is_correct': int(not responded),
        }