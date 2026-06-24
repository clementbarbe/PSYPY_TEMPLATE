"""
Task package — lazy registration.
"""

from tasks.registry import register_lazy, get_task, list_tasks

register_lazy('flanker', 'tasks.flanker', 'FlankerTask')
register_lazy('nback',   'tasks.nback',   'NBackTask')
register_lazy('stroop',  'tasks.stroop',  'StroopTask')
register_lazy('oddball', 'tasks.oddball', 'OddballTask')

__all__ = ['get_task', 'list_tasks']