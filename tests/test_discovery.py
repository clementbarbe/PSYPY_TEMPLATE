"""Tests de découverte dynamique des tâches."""

from tasks import list_tasks, load_task_class, load_task_config


def test_expected_tasks_discovered() -> None:
    """Les quatre tâches distribuées doivent être visibles automatiquement."""
    assert {"flanker", "nback", "oddball", "stroop"} <= set(list_tasks())


def test_every_task_has_config_and_class() -> None:
    """Chaque dossier détecté doit exposer config et classe Task."""
    for task_name in list_tasks():
        config = load_task_config(task_name)
        task_class = load_task_class(task_name)
        assert config["name"]
        assert config["designs"]
        assert task_class is not None


def test_stroop_dry_run() -> None:
    """Le Stroop complet doit se valider sans importer PsychoPy."""
    config = load_task_config("stroop")
    load_task_class("stroop").dry_run(task_config=config, design_id=4, seed=123)
