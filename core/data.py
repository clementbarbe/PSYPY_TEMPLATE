"""Écriture BIDS des événements avec sauvegarde incrémentale robuste."""

from __future__ import annotations

import csv
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.config import SessionSettings
from core.logging import ExperimentLogger


NA = "n/a"
PREFERRED_COLUMNS = [
    "onset", "duration", "trial_type", "response_time", "response_key",
    "block_index", "trial_index", "trial_index_global", "is_correct",
]


class OutputPaths:
    """Construit une arborescence BIDS ``sub-*/ses-*/func``."""

    def __init__(self, settings: SessionSettings) -> None:
        """Mémorise les paramètres nécessaires à la construction des chemins."""
        self.settings = settings

    @property
    def subject_dir(self) -> Path:
        """Dossier du participant."""
        return self.settings.data_dir / f"sub-{self.settings.participant}"

    @property
    def session_dir(self) -> Path:
        """Dossier de la session."""
        return self.subject_dir / f"ses-{self.settings.session}"

    @property
    def func_dir(self) -> Path:
        """Dossier BIDS fonctionnel contenant événements et plans."""
        return self.session_dir / "func"

    @property
    def log_dir(self) -> Path:
        """Dossier des logs opérateur, séparé des fichiers BIDS fonctionnels."""
        return self.session_dir / "logs"

    def ensure(self) -> None:
        """Crée les dossiers requis sans supprimer de données existantes."""
        self.func_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def stem(self, task_name: str, run: str) -> str:
        """Retourne le préfixe BIDS commun d'un run."""
        return (
            f"sub-{self.settings.participant}_ses-{self.settings.session}"
            f"_task-{task_name}_run-{run}"
        )

    def resolve_run(self, task_name: str) -> str:
        """Résout le run demandé ou choisit le premier numéro libre."""
        self.ensure()
        if self.settings.requested_run is not None:
            run = self.settings.requested_run
            if list(self.func_dir.glob(f"{self.stem(task_name, run)}*")):
                raise FileExistsError(
                    f"Le run {run} existe déjà pour task={task_name}; "
                    "choisir un autre run pour éviter tout écrasement."
                )
            return run

        for index in range(1, 1000):
            run = f"{index:02d}"
            if not list(self.func_dir.glob(f"{self.stem(task_name, run)}*")):
                return run
        raise RuntimeError("Impossible de trouver un numéro de run libre (<1000).")


class DataWriter:
    """Écrit chaque essai immédiatement puis finalise atomiquement le TSV.

    Le fichier ``*_events.inprogress.tsv`` reste lisible après un crash. À la
    fin normale, un fichier BIDS ``*_events.tsv`` est écrit via ``os.replace``.
    """

    def __init__(
        self,
        *,
        output_dir: Path,
        stem: str,
        logger: ExperimentLogger,
        enabled: bool = True,
    ) -> None:
        """Initialise un writer sans ouvrir de fichier persistant."""
        self.output_dir = Path(output_dir)
        self.stem = stem
        self.logger = logger
        self.enabled = bool(enabled)
        self.records: list[dict[str, Any]] = []
        self.headers: list[str] = []
        self.incremental_path = self.output_dir / f"{self.stem}_events.inprogress.tsv"
        self.final_path = self.output_dir / f"{self.stem}_events.tsv"
        self.sidecar_path = self.output_dir / f"{self.stem}_events.json"
        self.run_metadata_path = self.output_dir / f"{self.stem}_run.json"
        self._file = None
        self._writer = None
        self._closed = False

    @property
    def n_trials(self) -> int:
        """Nombre d'essais reçus en mémoire."""
        return len(self.records)

    def write_trial(self, record: dict[str, Any]) -> None:
        """Ajoute un essai et le synchronise immédiatement sur disque.

        Le chemin normal est un simple append, afin de minimiser l'I/O entre
        deux essais. Une réécriture n'a lieu que si une nouvelle colonne
        apparaît après le premier trial.
        """
        self.records.append(deepcopy(record))
        if not self.enabled:
            return

        late_columns = [column for column in record if column not in self.headers]
        if late_columns:
            self.headers = order_columns(self.headers + late_columns)

        if self._writer is None:
            # Premier essai : crée en-tête + ligne de manière atomique, puis
            # ouvre le fichier en append pour les essais suivants.
            self._write_table_atomic(self.incremental_path, self.records, self.headers)
            self._open_incremental_append()
            return

        if late_columns:
            # Cas exceptionnel : ferme l'append, réécrit avec le nouveau schéma
            # puis reprend les écritures incrémentales.
            self._close_incremental_handle()
            self._write_table_atomic(self.incremental_path, self.records, self.headers)
            self._open_incremental_append()
            return

        row = {column: clean_value(record.get(column)) for column in self.headers}
        self._writer.writerow(row)
        self._file.flush()
        try:
            os.fsync(self._file.fileno())
        except OSError:
            pass

    def save_final(self) -> Path | None:
        """Finalise le fichier ``events.tsv`` et vérifie le nombre de lignes."""
        if not self.enabled:
            self.logger.warning("Sauvegarde désactivée pour ce run.")
            return None
        if not self.records:
            self.logger.warning("Aucun essai à sauvegarder.")
            return None

        self.headers = order_columns(self.headers or list(self.records[0]))
        self._close_incremental_handle()
        self._write_table_atomic(self.final_path, self.records, self.headers)
        if count_rows(self.final_path) != len(self.records):
            raise RuntimeError("Vérification post-écriture des événements échouée.")

        self.logger.ok(f"Données BIDS sauvegardées : {self.final_path.name}")
        return self.final_path

    def write_sidecar(self, metadata: dict[str, Any]) -> Path | None:
        """Écrit atomiquement le sidecar JSON associé à ``events.tsv``."""
        if not self.enabled:
            return None
        self.output_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.sidecar_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        os.replace(temporary, self.sidecar_path)
        return self.sidecar_path

    def close(self) -> None:
        """Ferme le handle incrémental de manière idempotente."""
        if self._closed:
            return
        self._closed = True
        self._close_incremental_handle()

    def write_run_metadata(self, metadata: dict[str, Any]) -> Path | None:
        """Conserve les paramètres et l'état du run, même sans essai terminé."""
        if not self.enabled:
            return None
        self.output_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.run_metadata_path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2, default=str)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.run_metadata_path)
        return self.run_metadata_path

    def _open_incremental_append(self) -> None:
        """Ouvre le fichier de secours en append après création de son en-tête."""
        self._file = self.incremental_path.open("a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(
            self._file,
            fieldnames=self.headers,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )

    def _close_incremental_handle(self) -> None:
        """Flush, fsync et ferme le handle d'append s'il est ouvert."""
        if self._file is None:
            self._writer = None
            return
        try:
            self._file.flush()
            try:
                os.fsync(self._file.fileno())
            except OSError:
                pass
            self._file.close()
        finally:
            self._file = None
            self._writer = None

    def _write_table_atomic(
        self,
        destination: Path,
        records: list[dict[str, Any]],
        headers: list[str],
    ) -> None:
        """Écrit une table TSV dans un temporaire puis remplace la destination."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp")
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=headers,
                delimiter="\t",
                lineterminator="\n",
                extrasaction="ignore",
            )
            writer.writeheader()
            for record in records:
                writer.writerow({column: clean_value(record.get(column)) for column in headers})
            stream.flush()
            try:
                os.fsync(stream.fileno())
            except OSError:
                pass
        os.replace(temporary, destination)


def order_columns(columns: list[str]) -> list[str]:
    """Place les colonnes BIDS principales avant les champs spécifiques."""
    unique = list(dict.fromkeys(columns))
    first = [column for column in PREFERRED_COLUMNS if column in unique]
    return first + [column for column in unique if column not in first]


def clean_value(value: Any) -> str:
    """Convertit une valeur Python en cellule TSV BIDS sûre."""
    if value is None or value == "":
        return NA
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def count_rows(path: Path) -> int:
    """Compte les lignes de données d'un TSV en excluant son en-tête."""
    with Path(path).open("r", encoding="utf-8") as stream:
        return max(0, sum(1 for _ in stream) - 1)
