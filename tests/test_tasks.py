"""Tests for task infrastructure."""

import pytest
from tasks.registry import get_task, list_tasks


class TestTaskRegistry:
    def test_flanker_registered(self):
        assert get_task('flanker') is not None

    def test_nback_registered(self):
        assert get_task('nback') is not None

    def test_unknown_returns_none(self):
        assert get_task('nonexistent_task') is None

    def test_list_tasks(self):
        tasks = list_tasks()
        assert 'flanker' in tasks
        assert 'nback' in tasks


class TestTaskConfig:
    def test_load_flanker_config(self):
        from config.tasks_config import load_task_config
        cfg = load_task_config('flanker')
        assert 'designs' in cfg
        assert 1 in cfg['designs']

    def test_load_nback_config(self):
        from config.tasks_config import load_task_config
        cfg = load_task_config('nback')
        assert 'designs' in cfg