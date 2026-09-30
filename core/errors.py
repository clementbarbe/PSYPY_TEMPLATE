"""Exceptions explicites du framework expérimental."""


class AbortExperiment(Exception):
    """Signale une interruption utilisateur ou matérielle contrôlée."""


class TaskConfigurationError(ValueError):
    """Signale une configuration de tâche ou de design invalide."""


class DesignError(ValueError):
    """Signale l'impossibilité de construire un design expérimental valide."""
