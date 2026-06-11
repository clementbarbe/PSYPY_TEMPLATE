"""
Task registry — lazy import to avoid loading PsychoPy at startup.

Tasks are registered with a module path + class name.
PsychoPy is only imported when get_task() resolves the class.

Usage in tasks/__init__.py::

    register_lazy('flanker', 'tasks.flanker', 'FlankerTask')

Usage at runtime::

    task_cls = get_task('flanker')   # imports tasks.flanker NOW
"""

from __future__ import annotations

import importlib
from typing import Type

# Entries are either:
#   - a class (already imported)
#   - a string "module.path:ClassName" (lazy)
_REGISTRY: dict[str, Type | str] = {}


def register_task(name: str):
    """
    Class decorator — registers a task class under *name*.

    Can still be used if you want eager registration, but
    the preferred method is register_lazy() from __init__.py.
    """
    def decorator(cls):
        _REGISTRY[name.lower()] = cls
        return cls
    return decorator


def register_lazy(name: str, module_path: str, class_name: str) -> None:
    """
    Register a task without importing its module.

    The module is imported on first call to get_task(name).
    This avoids loading PsychoPy when only the GUI/registry is needed.

    Args:
        name: task name (e.g. 'flanker')
        module_path: dotted module path (e.g. 'tasks.flanker')
        class_name: class name in that module (e.g. 'FlankerTask')
    """
    _REGISTRY[name.lower()] = f"{module_path}:{class_name}"


def get_task(name: str) -> Type | None:
    """
    Return task class for *name*, importing lazily if needed.

    Returns None if task is not registered.
    """
    entry = _REGISTRY.get(name.lower())
    if entry is None:
        return None

    # Already resolved to a class
    if not isinstance(entry, str):
        return entry

    # Lazy import: "module.path:ClassName"
    try:
        module_path, class_name = entry.split(':')
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        # Cache the resolved class for future calls
        _REGISTRY[name.lower()] = cls
        return cls
    except Exception as e:
        import sys
        print(
            f"[ERROR] Failed to import task '{name}' "
            f"from {entry}: {e}",
            file=sys.stderr,
        )
        return None


def list_tasks() -> list[str]:
    """Return sorted list of registered task names (no imports triggered)."""
    return sorted(_REGISTRY.keys())