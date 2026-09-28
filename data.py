"""
Gestion des données :
- structure sub-*/ses-* ;
- logs ;
- TSV incrémental ;
- sauvegarde finale atomique ;
- résolution automatique des numéros de run.
"""

from __future__ import annotations

import csv
import os
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path


NA = "n/a"

PREFERRED_COLUMNS = [
    "onset",
    "duration",
    "trial_type",
    "participant",
    "session",
    "run",
    "task",
    "design_id",
    "design_name",
    "seed",
    "block_index",
    "block_condition",
    "trial_index",
    "trial_index_global",
]


class Logger:
    """Logger volontairement léger : console + fichier."""

    def __init__(self, log_dir: Path):
        log_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = log_dir / f"experiment_{stamp}.log"
        self._file = self.path.open("a", encoding="utf-8")
        self._closed = False

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def ok(self, message: str) -> None:
        self._write("OK", message)

    def warning(self, message: str) -> None:
        self._write("WARN", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def _write(self, level: str, message: str) -> None:
        if self._closed:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{level:5}] {message}"

        try:
            print(line, file=sys.stderr, flush=True)
        except Exception:
            pass

        try:
            self._file.write(line + "\n")
            self._file.flush()
        except Exception:
            pass

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        try:
            self._file.close()
        except Exception:
            pass


class OutputPaths:
    """Construit les chemins de sortie BIDS-like."""

    def __init__(self, settings):
        self.settings = settings

    @property
    def subject_dir(self) -> Path:
        return (
            self.settings.data_dir
            / f"sub-{self.settings.participant}"
            / f"ses-{self.settings.session}"
        )

    @property
    def log_dir(self) -> Path:
        return self.subject_dir / "logs"

    def task_dir(self, task_name: str) -> Path:
        return self.subject_dir / task_name

    def ensure_task_dir(self, task_name: str) -> Path:
        folder = self.task_dir(task_name)
        folder.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        return folder

    def stem(self, task_name: str, design_id: int | str, run: str) -> str:
        return (
            f"sub-{self.settings.participant}"
            f"_ses-{self.settings.session}"
            f"_task-{task_name}"
            f"_design-{design_id}"
            f"_run-{run}"
        )

    def resolve_run(self, task_name: str, design_id: int | str) -> str:
        folder = self.ensure_task_dir(task_name)

        for index in range(1, 100):
            run = f"{index:02d}"
            stem = self.stem(task_name, design_id, run)

            if not list(folder.glob(f"{stem}*")):
                return run

        raise RuntimeError(
            f"Plus de 99 runs trouvés pour task={task_name}, design={design_id}."
        )


class DataWriter:
    """
    Écriture TSV incrémentale.

    - Chaque essai est flushé immédiatement.
    - Une copie finale atomique est produite à la fin.
    - enabled=False permet de lancer sans sauvegarder.
    """

    def __init__(
        self,
        output_dir: Path,
        stem: str,
        logger: Logger,
        enabled: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.stem = stem
        self.logger = logger
        self.enabled = enabled

        self.records: list[dict] = []
        self.headers: list[str] | None = None
        self.incremental_path: Path | None = None

        self._file = None
        self._writer = None
        self._closed = False

    @property
    def n_trials(self) -> int:
        return len(self.records)

    def write_trial(self, record: dict) -> None:
        self.records.append(deepcopy(record))

        if not self.enabled:
            return

        if self.headers is None:
            self.headers = order_columns(list(record))
            self._open_incremental()

        assert self.headers is not None
        assert self._writer is not None
        assert self._file is not None

        late_columns = set(record) - set(self.headers)

        if late_columns:
            self.logger.warning(
                f"Colonnes apparues après le premier essai et ignorées : "
                f"{sorted(late_columns)}"
            )

        row = {column: clean_value(record.get(column)) for column in self.headers}

        self._writer.writerow(row)
        self._file.flush()

        try:
            os.fsync(self._file.fileno())
        except OSError:
            pass

    def save_final(self) -> Path | None:
        if not self.enabled:
            self.logger.warning("Sauvegarde désactivée (--no-save).")
            return None

        if not self.records:
            self.logger.warning("Aucun essai à sauvegarder.")
            return None

        headers = self.headers or order_columns(list(self.records[0]))
        final = self.output_dir / f"{self.stem}_events.tsv"
        temporary = final.with_suffix(".tsv.tmp")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            with temporary.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=headers,
                    delimiter="\t",
                    lineterminator="\n",
                    extrasaction="ignore",
                )
                writer.writeheader()

                for record in self.records:
                    writer.writerow(
                        {
                            column: clean_value(record.get(column))
                            for column in headers
                        }
                    )

                file.flush()

                try:
                    os.fsync(file.fileno())
                except OSError:
                    pass

            os.replace(temporary, final)

            count = count_rows(final)

            if count != len(self.records):
                raise RuntimeError(
                    f"Nombre de lignes invalide : "
                    f"{count} sur disque / {len(self.records)} en mémoire."
                )

            self.logger.ok(
                f"Données sauvegardées : {final.name} "
                f"({count} essais vérifiés)"
            )

            return final

        except Exception as exc:
            self.logger.error(f"Sauvegarde finale impossible : {exc}")

            try:
                temporary.unlink(missing_ok=True)
            except Exception:
                pass

            return None

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        if self._file is not None:
            try:
                self._file.flush()
                self._file.close()
            except Exception:
                pass

        self._file = None

    def _open_incremental(self) -> None:
        assert self.headers is not None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.incremental_path = (
            self.output_dir / f"{self.stem}_events_incremental.tsv"
        )

        self._file = self.incremental_path.open(
            "w",
            newline="",
            encoding="utf-8",
        )

        self._writer = csv.DictWriter(
            self._file,
            fieldnames=self.headers,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )

        self._writer.writeheader()
        self._file.flush()

        self.logger.info(f"Fichier incrémental : {self.incremental_path.name}")


def order_columns(columns: list[str]) -> list[str]:
    first = [column for column in PREFERRED_COLUMNS if column in columns]
    remaining = [column for column in columns if column not in first]
    return first + remaining


def clean_value(value) -> str:
    if value is None or value == "":
        return NA

    if isinstance(value, bool):
        return "1" if value else "0"

    if isinstance(value, float):
        return f"{value:.6g}"

    return str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8") as file:
        return max(0, sum(1 for _ in file) - 1)