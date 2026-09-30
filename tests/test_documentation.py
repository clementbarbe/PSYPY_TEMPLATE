"""Vérifie que le code publié reste documenté à mesure qu'il évolue."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_DIRS = [ROOT / "core", ROOT / "hardware", ROOT / "gui", ROOT / "tasks"]


def test_public_classes_and_functions_have_docstrings() -> None:
    """Chaque classe/fonction du framework doit avoir une docstring."""
    missing: list[str] = []
    files = [ROOT / "main.py"]
    for folder in PUBLISHED_DIRS:
        files.extend(folder.rglob("*.py"))
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    missing.append(f"{path.relative_to(ROOT)}:{node.lineno} {node.name}")
    assert not missing, "Docstrings manquantes:\n" + "\n".join(missing)
