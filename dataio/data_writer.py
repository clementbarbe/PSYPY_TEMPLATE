"""
Incremental CSV data writer with final save.

Writes each trial as soon as it happens (crash-safe).
"""

from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path

from dataio.logger import ExperimentLogger


class DataWriter:
    """Write trial records to CSV incrementally."""

    def __init__(
        self,
        output_dir: Path,
        filename: str,
        logger: ExperimentLogger,
    ):
        self._output_dir = Path(output_dir)
        self._filename = filename
        self._logger = logger
        self._records: list[dict] = []
        self._headers: list[str] | None = None
        self._file = None
        self._writer = None
        self._filepath: Path | None = None

    def write_trial(self, record: dict) -> None:
        """Append one trial record (written to disk immediately)."""
        self._records.append(deepcopy(record))
        if self._headers is None:
            self._init_file(list(record.keys()))
        try:
            self._writer.writerow(record)
            self._file.flush()
        except Exception as e:
            self._logger.warn(f"DataWriter write error: {e}")

    @property
    def records(self) -> list[dict]:
        return self._records

    @property
    def filepath(self) -> Path | None:
        return self._filepath

    @property
    def n_trials(self) -> int:
        return len(self._records)

    def save_final(self, suffix: str = '_final') -> Path | None:
        """Write a clean copy of all records to a separate file."""
        if not self._records:
            return None
        path = self._output_dir / f"{self._filename}{suffix}.csv"
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self._headers)
                writer.writeheader()
                writer.writerows(self._records)
            self._logger.ok(f"Final data saved: {path}")
            return path
        except Exception as e:
            self._logger.err(f"Final save failed: {e}")
            return None

    def close(self) -> None:
        if self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None

    def _init_file(self, headers: list[str]) -> None:
        self._headers = headers
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._filepath = self._output_dir / f"{self._filename}.csv"
        try:
            self._file = open(self._filepath, 'w', newline='', encoding='utf-8')
            self._writer = csv.DictWriter(self._file, fieldnames=self._headers)
            self._writer.writeheader()
            self._file.flush()
            self._logger.ok(f"Data file created: {self._filepath}")
        except Exception as e:
            self._logger.err(f"Cannot create data file: {e}")
            raise

    def __del__(self):
        self.close()