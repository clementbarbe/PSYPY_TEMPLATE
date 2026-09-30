"""Garde-fou sur l'API de BaseTask."""

from tasks.base import BaseTask


def test_task_run_method_is_not_shadowed() -> None:
    """BaseTask.run doit rester une méthode appelable."""
    assert callable(BaseTask.run)
