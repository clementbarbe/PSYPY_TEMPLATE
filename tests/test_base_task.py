from tasks.base import BaseTask


def test_task_run_method_is_not_shadowed():
    """
    Le nom de méthode BaseTask.run ne doit jamais être remplacé
    par un attribut d'instance contenant le numéro de run.
    """
    assert callable(BaseTask.run)