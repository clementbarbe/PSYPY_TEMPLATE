"""Découverte automatique des tâches expérimentales.

Une tâche est un dossier ``tasks/<nom>/`` contenant ``task.py`` et
``config.yaml``. Aucun registre central n'est nécessaire.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Type

import yaml


TASKS_DIR = Path(__file__).resolve().parent


def discover_tasks() -> dict[str, Path]:
    """Retourne les dossiers de tâches valides indexés par leur nom."""
    discovered: dict[str, Path] = {}
    for folder in sorted(TASKS_DIR.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        if (folder / "task.py").exists() and (folder / "config.yaml").exists():
            discovered[folder.name.lower()] = folder
    return discovered


def list_tasks() -> list[str]:
    """Retourne les noms de tâches détectées, triés alphabétiquement."""
    return sorted(discover_tasks())


def get_task_dir(task_name: str) -> Path:
    """Retourne le dossier d'une tâche ou lève une erreur explicite."""
    name = task_name.lower()
    try:
        return discover_tasks()[name]
    except KeyError as exc:
        available = ", ".join(list_tasks()) or "aucune"
        raise ValueError(
            f"Tâche inconnue : {task_name!r}. Disponibles : {available}"
        ) from exc


def load_task_config(task_name: str) -> dict:
    """Charge et valide le ``config.yaml`` d'une tâche."""
    path = get_task_dir(task_name) / "config.yaml"
    try:
        with path.open("r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML invalide dans : {path}") from exc

    if not config.get("name"):
        raise ValueError(f"Champ YAML 'name' manquant dans {path}")
    if not config.get("designs"):
        raise ValueError(f"Champ YAML 'designs' manquant ou vide dans {path}")

    config["designs"] = {
        int(key) if str(key).isdigit() else key: value
        for key, value in config["designs"].items()
    }
    return config


def load_task_class(task_name: str) -> Type:
    """Importe la classe ``Task`` d'une tâche de façon standard et testable."""
    name = task_name.lower()
    get_task_dir(name)
    module = importlib.import_module(f"tasks.{name}.task")
    task_class = getattr(module, "Task", None)
    if task_class is None:
        raise TypeError(f"tasks/{name}/task.py doit définir une classe Task.")

    from tasks.base import BaseTask

    if not isinstance(task_class, type) or not issubclass(task_class, BaseTask):
        raise TypeError(f"Task dans tasks/{name}/task.py doit hériter de BaseTask.")
    return task_class
