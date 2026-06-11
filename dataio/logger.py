"""
Structured experiment logger — Windows compatible.

Writes to both console (coloured) and a log file.
ANSI colours are enabled via utils.console.init_console().
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from config.settings import ExperimentSettings


class ExperimentLogger:
    """Session-wide logger with file + console output."""

    _COLORS = {
        'LOG':  '\033[37m',
        'OK':   '\033[92m',
        'WARN': '\033[93m',
        'ERR':  '\033[91m',
        'RESET': '\033[0m',
    }

    def __init__(self, settings: ExperimentSettings | None = None):
        self._file = None
        self._closed = False
        if settings is not None:
            log_dir = settings.log_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_path = (
                log_dir
                / f"sub-{settings.participant_id}_ses-{settings.session}_{ts}.log"
            )
            try:
                self._file = open(log_path, 'a', encoding='utf-8')
            except Exception as e:
                print(f"[WARN] Cannot open log file: {e}", file=sys.stderr)

    def log(self, msg: str) -> None:
        self._write('LOG', msg)

    def ok(self, msg: str) -> None:
        self._write('OK', msg)

    def warn(self, msg: str) -> None:
        self._write('WARN', msg)

    def err(self, msg: str) -> None:
        self._write('ERR', msg)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None

    def _write(self, level: str, msg: str) -> None:
        if self._closed:
            return
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        line = f"[{ts}] [{level:4s}] {msg}"

        # Console
        try:
            color = self._COLORS.get(level, '')
            reset = self._COLORS['RESET']
            print(f"{color}{line}{reset}", file=sys.stderr, flush=True)
        except (UnicodeEncodeError, OSError):
            # Fallback: no color, safe encoding
            try:
                ascii_line = line.encode('ascii', errors='replace').decode('ascii')
                print(ascii_line, file=sys.stderr, flush=True)
            except Exception:
                pass

        # File
        if self._file is not None:
            try:
                self._file.write(line + '\n')
                self._file.flush()
            except Exception:
                pass

    def __del__(self):
        self.close()