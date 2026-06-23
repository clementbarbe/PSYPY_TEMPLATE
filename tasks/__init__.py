"""
Task package — lazy registration.
PsychoPy is NOT imported until get_task() is called.
"""

from tasks.registry import register_lazy, get_task, list_tasks

register_lazy('flanker', 'tasks.flanker', 'FlankerTask')
register_lazy('nback',   'tasks.nback',   'NBackTask')
register_lazy('stroop',  'tasks.stroop',  'StroopTask')

__all__ = ['get_task', 'list_tasks']