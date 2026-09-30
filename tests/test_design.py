"""Tests du générateur de design commun."""

import random

import pytest

from core.design import DesignGenerator
from core.errors import DesignError


def test_same_seed_produces_same_generic_design() -> None:
    """Une graine identique doit reproduire exactement le même plan."""
    kwargs = dict(
        conditions=["A", "B"],
        n_blocks=3,
        trials_per_block=10,
        max_consecutive=3,
        iti=(1.0, 2.0),
        seed=42,
    )
    assert DesignGenerator(**kwargs).generate().blocks == DesignGenerator(**kwargs).generate().blocks


def test_balanced_conditions_by_block() -> None:
    """Chaque bloc doit rester équilibré à un essai près."""
    design = DesignGenerator(
        conditions=["A", "B", "C"],
        n_blocks=2,
        trials_per_block=20,
        max_consecutive=3,
        seed=7,
    ).generate()
    for block in design.blocks:
        counts = {name: sum(t["condition"] == name for t in block) for name in ["A", "B", "C"]}
        assert max(counts.values()) - min(counts.values()) <= 1


def test_shuffle_constrained_respects_limit() -> None:
    """Le helper de pseudo-randomisation respecte max_consecutive."""
    rng = random.Random(123)
    items = ["A"] * 6 + ["B"] * 6
    ordered = DesignGenerator.shuffle_constrained(
        items, rng=rng, key=lambda value: value, max_consecutive=2
    )
    assert DesignGenerator.max_run(ordered, key=lambda value: value) <= 2


def test_impossible_constraint_is_explicit() -> None:
    """Une contrainte mathématiquement impossible ne doit pas boucler silencieusement."""
    with pytest.raises(DesignError):
        DesignGenerator.shuffle_constrained(
            ["A"] * 10 + ["B"],
            rng=random.Random(1),
            key=lambda value: value,
            max_consecutive=2,
            max_attempts=50,
        )
