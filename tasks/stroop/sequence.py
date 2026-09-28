"""
Génération de séquences Stroop équilibrées.

Garanties :
- équilibre approximatif des catégories ;
- pas plus de deux mêmes mots consécutifs ;
- pas plus de deux mêmes encres consécutives ;
- dans les designs event-related :
  jamais deux trial_type identiques consécutifs ;
- reproductibilité complète via le RNG passé en argument.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable


TRIAL_TYPES = ("neutral", "congruent", "incongruent")


def split_evenly(total: int, categories: list[str], rng) -> dict[str, int]:
    """
    Répartit total entre les catégories avec un écart maximal de 1.

    Exemple :
        split_evenly(25, ["a", "b", "c"], rng)
        -> {"a": 9, "b": 8, "c": 8}
    """
    if not categories:
        return {}

    result = {
        category: total // len(categories)
        for category in categories
    }

    remainder = total % len(categories)
    extras = list(categories)
    rng.shuffle(extras)

    for category in extras[:remainder]:
        result[category] += 1

    return result


def max_run(values: Iterable) -> int:
    """Retourne la longueur maximale d'une répétition consécutive."""
    values = list(values)

    if not values:
        return 0

    longest = 1
    current = 1

    for previous, value in zip(values, values[1:]):
        if value == previous:
            current += 1
        else:
            current = 1

        longest = max(longest, current)

    return longest


def _would_break_run(
    output: list[dict],
    candidate: dict,
    key: str,
    maximum: int,
) -> bool:
    """
    Retourne True si ajouter candidate à output créerait une répétition
    supérieure à maximum pour candidate[key].
    """
    if maximum <= 0:
        return False

    if len(output) < maximum:
        return False

    value = candidate[key]

    return all(
        previous[key] == value
        for previous in output[-maximum:]
    )


def _valid_candidate(
    output: list[dict],
    candidate: dict,
    max_same_word: int,
    max_same_ink: int,
    max_same_type: int | None,
) -> bool:
    """Teste les contraintes locales avant d'ajouter un essai."""

    if _would_break_run(output, candidate, "word", max_same_word):
        return False

    if _would_break_run(output, candidate, "ink", max_same_ink):
        return False

    if max_same_type is not None:
        if _would_break_run(
            output,
            candidate,
            "trial_type",
            max_same_type,
        ):
            return False

    return True


def _build_type_schedule(
    trials: list[dict],
    rng,
) -> list[str] | None:
    """
    Construit un ordre de trial_type où deux types successifs diffèrent.

    Cette construction est déterministe conditionnellement au RNG et
    respecte exactement les comptes de chaque type.
    """
    remaining = Counter(trial["trial_type"] for trial in trials)
    total = len(trials)

    schedule: list[str] = []
    previous = None

    for _ in range(total):
        candidates = [
            trial_type
            for trial_type, count in remaining.items()
            if count > 0 and trial_type != previous
        ]

        if not candidates:
            return None

        largest_count = max(remaining[trial_type] for trial_type in candidates)

        largest = [
            trial_type
            for trial_type in candidates
            if remaining[trial_type] == largest_count
        ]

        chosen = rng.choice(largest)

        schedule.append(chosen)
        remaining[chosen] -= 1
        previous = chosen

    return schedule


def _choose_candidate(
    candidates: list[dict],
    remaining_trials: list[dict],
    rng,
) -> dict:
    """
    Choisit un essai admissible.

    Les mots/encres les plus fréquents restants sont préférés afin
    d'éviter de laisser à la fin une catégorie impossible à placer.
    """
    word_remaining = Counter(trial["word"] for trial in remaining_trials)
    ink_remaining = Counter(trial["ink"] for trial in remaining_trials)

    scores = {
        id(candidate): (
            word_remaining[candidate["word"]]
            + ink_remaining[candidate["ink"]]
        )
        for candidate in candidates
    }

    best_score = max(scores.values())

    best = [
        candidate
        for candidate in candidates
        if scores[id(candidate)] == best_score
    ]

    return rng.choice(best)


def order_trials(
    trials: list[dict],
    rng,
    max_same_word: int = 2,
    max_same_ink: int = 2,
    max_same_type: int | None = None,
    attempts: int = 500,
) -> list[dict]:
    """
    Ordonne les essais sous contraintes.

    Contrairement à la version précédente, cette fonction ne dépend pas
    d'une improbable permutation aléatoire satisfaisant toutes les règles.

    Si max_same_type == 1, un planning explicite des trial_type est
    construit avant le placement des essais. C'est nécessaire pour le
    Stroop event-related.
    """
    source = list(trials)

    if len(source) <= 1:
        return source

    for _ in range(attempts):
        remaining = list(source)
        rng.shuffle(remaining)
        output: list[dict] = []

        type_schedule = None

        if max_same_type == 1:
            type_schedule = _build_type_schedule(remaining, rng)

            if type_schedule is None:
                continue

        success = True

        for position in range(len(source)):
            if type_schedule is None:
                eligible = [
                    trial
                    for trial in remaining
                    if _valid_candidate(
                        output,
                        trial,
                        max_same_word=max_same_word,
                        max_same_ink=max_same_ink,
                        max_same_type=max_same_type,
                    )
                ]
            else:
                required_type = type_schedule[position]

                eligible = [
                    trial
                    for trial in remaining
                    if trial["trial_type"] == required_type
                    and _valid_candidate(
                        output,
                        trial,
                        max_same_word=max_same_word,
                        max_same_ink=max_same_ink,
                        max_same_type=max_same_type,
                    )
                ]

            if not eligible:
                success = False
                break

            chosen = _choose_candidate(
                candidates=eligible,
                remaining_trials=remaining,
                rng=rng,
            )

            output.append(chosen)
            remaining.remove(chosen)

        if success:
            return output

    raise RuntimeError(
        "Impossible de produire une séquence Stroop valide "
        f"après {attempts} tentatives."
    )


def valid_order(
    trials: list[dict],
    max_same_word: int,
    max_same_ink: int,
    max_same_type: int | None,
) -> bool:
    """Validation pure d'un ordre déjà construit."""

    if max_run([trial["word"] for trial in trials]) > max_same_word:
        return False

    if max_run([trial["ink"] for trial in trials]) > max_same_ink:
        return False

    if max_same_type is not None:
        if max_run([trial["trial_type"] for trial in trials]) > max_same_type:
            return False

    return True


def build_condition_trials(
    condition: str,
    count: int,
    colors: list[str],
    color_words: dict[str, str],
    neutral_words: list[str],
    rng,
) -> list[dict]:
    """Construit les essais d'une seule condition Stroop."""

    ink_counts = split_evenly(count, colors, rng)
    trials: list[dict] = []

    if condition == "congruent":
        for ink, n_trials in ink_counts.items():
            for _ in range(n_trials):
                trials.append(
                    {
                        "word": color_words[ink],
                        "ink": ink,
                        "trial_type": "congruent",
                    }
                )

        return trials

    if condition == "incongruent":
        pairs = [
            (word_color, ink)
            for ink in colors
            for word_color in colors
            if word_color != ink
        ]

        labels = [
            f"{word_color}|{ink}"
            for word_color, ink in pairs
        ]

        label_to_pair = {
            f"{word_color}|{ink}": (word_color, ink)
            for word_color, ink in pairs
        }

        pair_counts = split_evenly(count, labels, rng)

        for label, n_trials in pair_counts.items():
            word_color, ink = label_to_pair[label]

            for _ in range(n_trials):
                trials.append(
                    {
                        "word": color_words[word_color],
                        "ink": ink,
                        "trial_type": "incongruent",
                    }
                )

        return trials

    if condition == "neutral":
        words = list(neutral_words)
        rng.shuffle(words)

        ink_sequence: list[str] = []

        for ink, n_trials in ink_counts.items():
            ink_sequence.extend([ink] * n_trials)

        rng.shuffle(ink_sequence)

        for index, ink in enumerate(ink_sequence):
            trials.append(
                {
                    "word": words[index % len(words)],
                    "ink": ink,
                    "trial_type": "neutral",
                }
            )

        return trials

    raise ValueError(f"Condition Stroop inconnue : {condition}")


def build_event_trials(
    count: int,
    colors: list[str],
    color_words: dict[str, str],
    neutral_words: list[str],
    rng,
) -> list[dict]:
    """
    Construit et ordonne un design event-related équilibré.

    Les trois conditions sont équilibrées à +/- 1, puis l'ordre impose
    une alternance stricte des trial_type.
    """
    type_counts = split_evenly(count, list(TRIAL_TYPES), rng)
    trials: list[dict] = []

    for condition, n_trials in type_counts.items():
        trials.extend(
            build_condition_trials(
                condition=condition,
                count=n_trials,
                colors=colors,
                color_words=color_words,
                neutral_words=neutral_words,
                rng=rng,
            )
        )

    return order_trials(
        trials=trials,
        rng=rng,
        max_same_word=2,
        max_same_ink=2,
        max_same_type=1,
    )


def validate_sequence(
    blocks: list[list[dict]],
    event_related: bool,
) -> None:
    """Vérifie les contraintes nécessaires avant l'acquisition."""

    flat = [trial for block in blocks for trial in block]

    if not flat:
        raise ValueError("Séquence Stroop vide.")

    for block_index, block in enumerate(blocks):
        if not block:
            raise ValueError(f"Bloc Stroop vide : {block_index}")

        if max_run([trial["ink"] for trial in block]) > 2:
            raise ValueError(
                f"Plus de deux encres identiques successives "
                f"dans le bloc {block_index}."
            )

        if max_run([trial["word"] for trial in block]) > 2:
            raise ValueError(
                f"Plus de deux mots identiques successifs "
                f"dans le bloc {block_index}."
            )

    if event_related:
        trial_types = [trial["trial_type"] for trial in flat]

        if max_run(trial_types) > 1:
            raise ValueError(
                "Deux types d'essais identiques sont successifs "
                "dans le design event-related."
            )