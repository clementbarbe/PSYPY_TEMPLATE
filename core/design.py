"""Génération reproductible de designs bloc et event-related.

Le module fournit une API volontairement simple. Les tâches peuvent utiliser le
``DesignGenerator`` complet ou uniquement ses helpers de randomisation pour des
stimuli plus spécialisés (Stroop, N-Back, etc.).
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Hashable, Iterable, Sequence, TypeVar

from core.errors import DesignError


T = TypeVar("T")


@dataclass(slots=True)
class GeneratedDesign:
    """Plan expérimental matérialisé avant le lancement de la tâche."""

    blocks: list[list[dict[str, Any]]]
    seed: int
    paradigm: str

    @property
    def n_blocks(self) -> int:
        """Nombre de blocs du plan."""
        return len(self.blocks)

    @property
    def n_trials(self) -> int:
        """Nombre total d'essais du plan."""
        return sum(len(block) for block in self.blocks)

    def flattened(self) -> list[dict[str, Any]]:
        """Retourne les essais avec indices bloc/essai explicites."""
        rows: list[dict[str, Any]] = []
        global_index = 0
        for block_index, block in enumerate(self.blocks):
            for trial_index, trial in enumerate(block):
                row = {
                    "block_index": block_index,
                    "trial_index": trial_index,
                    "trial_index_global": global_index,
                    **deepcopy(trial),
                }
                rows.append(row)
                global_index += 1
        return rows


class DesignGenerator:
    """Construit des séquences équilibrées avec contraintes simples.

    Parameters
    ----------
    conditions:
        Noms des conditions à équilibrer.
    n_blocks:
        Nombre de blocs. Requis pour un design bloc générique.
    trials_per_block:
        Nombre d'essais par bloc. Peut être remplacé par ``total_trials``.
    total_trials:
        Nombre total d'essais ; doit être divisible par ``n_blocks`` lorsque
        ``trials_per_block`` n'est pas fourni.
    max_consecutive:
        Nombre maximal autorisé d'essais consécutifs partageant la même
        condition. ``None`` désactive cette contrainte.
    iti:
        ITI fixe (float) ou intervalle ``(min, max)``. Les intervalles sont
        stratifiés afin de couvrir régulièrement la plage avant mélange.
    seed:
        Graine RNG enregistrée avec le design pour une reproduction exacte.
    """

    def __init__(
        self,
        *,
        conditions: Sequence[str],
        n_blocks: int = 1,
        trials_per_block: int | None = None,
        total_trials: int | None = None,
        max_consecutive: int | None = None,
        iti: float | tuple[float, float] | None = None,
        seed: int | None = None,
        paradigm: str = "block",
    ) -> None:
        """Valide les paramètres puis initialise un RNG local reproductible."""
        if not conditions:
            raise DesignError("Au moins une condition est requise.")
        if n_blocks < 1:
            raise DesignError("n_blocks doit être >= 1.")
        if max_consecutive is not None and max_consecutive < 1:
            raise DesignError("max_consecutive doit être >= 1 ou None.")

        if trials_per_block is None:
            if total_trials is None:
                raise DesignError("Définir trials_per_block ou total_trials.")
            if total_trials % n_blocks:
                raise DesignError("total_trials doit être divisible par n_blocks.")
            trials_per_block = total_trials // n_blocks
        elif total_trials is not None and trials_per_block * n_blocks != total_trials:
            raise DesignError("trials_per_block * n_blocks doit égaler total_trials.")

        if trials_per_block < 1:
            raise DesignError("trials_per_block doit être >= 1.")

        self.conditions = list(conditions)
        self.n_blocks = int(n_blocks)
        self.trials_per_block = int(trials_per_block)
        self.max_consecutive = max_consecutive
        self.iti = iti
        self.seed = int(seed) if seed is not None else random.SystemRandom().randrange(2**31)
        self.paradigm = str(paradigm)
        self.rng = random.Random(self.seed)

    def generate(self) -> GeneratedDesign:
        """Génère le plan générique complet et déterministe."""
        blocks: list[list[dict[str, Any]]] = []
        for _ in range(self.n_blocks):
            counts = self.balanced_counts(self.conditions, self.trials_per_block, self.rng)
            sequence = [condition for condition, count in counts.items() for _ in range(count)]
            sequence = self.shuffle_constrained(
                sequence,
                rng=self.rng,
                key=lambda value: value,
                max_consecutive=self.max_consecutive,
            )
            itis = self._build_itis(len(sequence))
            block = []
            for index, condition in enumerate(sequence):
                trial: dict[str, Any] = {"condition": condition, "trial_type": condition}
                if itis is not None:
                    trial["iti"] = itis[index]
                block.append(trial)
            blocks.append(block)

        return GeneratedDesign(blocks=blocks, seed=self.seed, paradigm=self.paradigm)

    def _build_itis(self, count: int) -> list[float] | None:
        """Crée les ITI du générateur courant."""
        if self.iti is None:
            return None
        if isinstance(self.iti, tuple):
            values = self.stratified_jitter(count, self.iti[0], self.iti[1], self.rng)
            return [round(value, 4) for value in values]
        return [float(self.iti)] * count

    @staticmethod
    def balanced_counts(categories: Sequence[str], total: int, rng: random.Random) -> dict[str, int]:
        """Répartit ``total`` aussi équitablement que possible entre catégories."""
        if total < 0:
            raise DesignError("total doit être positif.")
        if not categories:
            raise DesignError("categories ne peut pas être vide.")

        base, remainder = divmod(total, len(categories))
        counts = {category: base for category in categories}
        order = list(categories)
        rng.shuffle(order)
        for category in order[:remainder]:
            counts[category] += 1
        return counts

    @staticmethod
    def shuffle_constrained(
        items: Sequence[T],
        *,
        rng: random.Random,
        key: Callable[[T], Hashable],
        max_consecutive: int | None,
        max_attempts: int = 2000,
    ) -> list[T]:
        """Mélange une séquence en limitant les répétitions consécutives.

        Une recherche par mélanges successifs suffit pour les designs usuels et
        reste beaucoup plus lisible qu'un solveur général. Si aucune permutation
        valide n'est trouvée, une erreur explicite demande d'assouplir le design.
        """
        result = list(items)
        if max_consecutive is None or len(result) < 2:
            rng.shuffle(result)
            return result

        for _ in range(max_attempts):
            rng.shuffle(result)
            if DesignGenerator.max_run(result, key=key) <= max_consecutive:
                return list(result)

        counts = Counter(key(item) for item in items)
        raise DesignError(
            "Pseudo-randomisation impossible avec max_consecutive="
            f"{max_consecutive}. Répartition observée : {dict(counts)}"
        )

    @staticmethod
    def max_run(items: Iterable[T], *, key: Callable[[T], Hashable]) -> int:
        """Retourne la longueur maximale d'une série de valeurs identiques."""
        longest = 0
        current = 0
        previous: Hashable | object = object()
        for item in items:
            value = key(item)
            if value == previous:
                current += 1
            else:
                previous = value
                current = 1
            longest = max(longest, current)
        return longest

    @staticmethod
    def stratified_jitter(
        count: int,
        minimum: float,
        maximum: float,
        rng: random.Random,
    ) -> list[float]:
        """Produit un jitter couvrant régulièrement ``[minimum, maximum]``."""
        if count < 1:
            return []
        if maximum < minimum:
            raise DesignError("Le maximum du jitter doit être >= au minimum.")
        if minimum == maximum:
            return [float(minimum)] * count

        values = [minimum + (maximum - minimum) * (i + 0.5) / count for i in range(count)]
        rng.shuffle(values)
        return values


def save_design_plan(
    blocks: list[list[dict[str, Any]]],
    *,
    json_path: Path,
    tsv_path: Path,
    metadata: dict[str, Any],
) -> None:
    """Sauvegarde le plan JSON et un TSV lisible avant l'acquisition.

    Le TSV est un *planned events file* : il documente l'ordre prévu, pas les
    onsets réellement mesurés. Les onsets réels sont écrits séparément par le
    ``DataWriter`` pendant l'acquisition.
    """
    json_path = Path(json_path)
    tsv_path = Path(tsv_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **deepcopy(metadata),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "blocks": deepcopy(blocks),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    rows: list[dict[str, Any]] = []
    all_columns: list[str] = ["block_index", "trial_index", "trial_index_global"]
    global_index = 0
    for block_index, block in enumerate(blocks):
        for trial_index, trial in enumerate(block):
            row = {
                "block_index": block_index,
                "trial_index": trial_index,
                "trial_index_global": global_index,
                **deepcopy(trial),
            }
            rows.append(row)
            global_index += 1
            for column in row:
                if column not in all_columns:
                    all_columns.append(column)

    with tsv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=all_columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _clean_design_value(row.get(key)) for key in all_columns})


def _clean_design_value(value: Any) -> str:
    """Convertit une valeur arbitraire en cellule TSV sûre."""
    if value is None or value == "":
        return "n/a"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")
