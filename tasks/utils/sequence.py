"""
Sequence generation utilities shared across tasks.

Provides de-sequencing, balanced randomisation, ISI generation.
"""

from __future__ import annotations

import random


def desequence(items: list, key_func=None,
               max_consecutive: int = 4,
               max_attempts: int = 100) -> list:
    """
    Shuffle *items* ensuring no more than *max_consecutive* identical
    values (determined by *key_func*) in a row.

    Args:
        items: list to shuffle
        key_func: callable returning the value to check for repeats
                  (default: identity)
        max_consecutive: max allowed consecutive identical values
        max_attempts: reshuffles before giving up

    Returns:
        Shuffled list (original is not modified).
    """
    result = list(items)
    if key_func is None:
        key_func = lambda x: x

    for _ in range(max_attempts):
        random.shuffle(result)
        if _check_no_long_runs(result, key_func, max_consecutive):
            return result

    return result  # best effort


def _check_no_long_runs(items, key_func, max_consecutive):
    for i in range(max_consecutive, len(items)):
        window = [key_func(items[j])
                  for j in range(i - max_consecutive, i + 1)]
        if len(set(window)) == 1:
            return False
    return True


def generate_jittered_isis(
    n: int,
    isi_min: float,
    isi_max: float,
) -> list[float]:
    """Generate *n* ISI durations uniformly distributed in [isi_min, isi_max]."""
    if abs(isi_min - isi_max) < 0.001:
        return [round(isi_min, 4)] * n
    return [round(random.uniform(isi_min, isi_max), 4) for _ in range(n)]