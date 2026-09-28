"""
Découverte automatique des tâches.

Une tâche valide est un dossier contenant :

    tasks/<nom>/
        task.py
        config.yaml

et `task.py` doit définir :

    class Task(BaseTask):
        ...
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


TASKS_DIR = Path(__file__).resolve().parent


def discover_tasks() -> dict[str, Path]:
    tasks: dict[str, Path] = {}

    for folder in sorted(TASKS_DIR.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue

        if (folder / "task.py").exists() and (folder / "config.yaml").exists():
            tasks[folder.name.lower()] = folder

    return tasks


def list_tasks() -> list[str]:
    return sorted(discover_tasks())


def get_task_dir(task_name: str) -> Path:
    name = task_name.lower()

    try:
        return discover_tasks()[name]
    except KeyError as exc:
        available = ", ".join(list_tasks()) or "aucune"
        raise ValueError(
            f"Tâche inconnue : '{task_name}'. Disponibles : {available}"
        ) from exc


def load_task_config(task_name: str) -> dict:
    path = get_task_dir(task_name) / "config.yaml"

    try:
        with path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}

    except yaml.YAMLError as exc:
        raise ValueError(f"YAML invalide dans : {path}") from exc

    if "name" not in config:
        raise ValueError(f"Champ YAML manquant : 'name' dans {path}")

    if "designs" not in config or not config["designs"]:
        raise ValueError(f"Champ YAML manquant ou vide : 'designs' dans {path}")

    config["designs"] = {
        int(key) if str(key).isdigit() else key: value
        for key, value in config["designs"].items()
    }

    return config


def load_task_class(task_name: str):
    folder = get_task_dir(task_name)
    source = folder / "task.py"
    module_name = f"_psychopy_task_{folder.name}"

    spec = importlib.util.spec_from_file_location(module_name, source)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger : {source}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    task_class = getattr(module, "Task", None)

    if task_class is None:
        raise TypeError(f"{source} doit définir une classe `Task`.")

    from tasks.base import BaseTask

    if not isinstance(task_class, type) or not issubclass(task_class, BaseTask):
        raise TypeError(f"`Task` dans {source} doit hériter de BaseTask.")

    return task_class