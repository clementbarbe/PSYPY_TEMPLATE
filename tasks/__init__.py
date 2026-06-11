"""
Task package — all experimental paradigms.

Tasks are registered LAZILY: only the name and module path are stored.
PsychoPy is NOT imported until get_task() is called at experiment runtime.

To add a new task:
    1. Create tasks/my_task.py with @register_task('my_task') on the class
    2. Add a register_lazy() line below
    3. Create config/tasks_config/my_task.yaml

To remove a task:
    1. Comment out or delete the register_lazy() line below
"""

from tasks.registry import register_lazy, get_task, list_tasks

# ══════════════════════════════════════════════════════════════════════
# Register tasks lazily — NO PsychoPy import happens here
# ══════════════════════════════════════════════════════════════════════

register_lazy('flanker', 'tasks.flanker', 'FlankerTask')
register_lazy('nback',   'tasks.nback',   'NBackTask')

# ── To add a new task, just add one line: ────────────────────────────
# register_lazy('stroop',  'tasks.stroop',  'StroopTask')
# register_lazy('gonogo',  'tasks.gonogo',  'GoNoGoTask')

__all__ = ['get_task', 'list_tasks']