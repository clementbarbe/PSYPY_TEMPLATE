"""Identification du code et de l'environnement effectifs avant acquisition."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform


def session_metadata(settings) -> dict:
    """Capture les paramètres, versions installées et empreinte des sources."""
    root = Path(__file__).resolve().parent.parent
    digest = sha256()
    paths = [root / "main.py"]
    for folder in ("core", "hardware", "tasks", "gui", "config"):
        paths.extend((root / folder).rglob("*.py"))
        paths.extend((root / folder).rglob("*.yaml"))
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(path.read_bytes())
    packages = {}
    for name in ("psychopy", "psychtoolbox", "PyQt6", "numpy", "PyYAML", "pyserial", "pylink", "tobii_research"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        "settings": asdict(settings), "source_sha256": digest.hexdigest(),
        "software_versions": packages, "python": platform.python_version(),
        "platform": platform.platform(),
    }
