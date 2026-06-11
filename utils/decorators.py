"""Useful decorators for timing and error handling."""

from __future__ import annotations

import time
import functools
from typing import Callable


def log_timing(logger=None):
    """Decorator: log execution time of a function."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - t0
            msg = f"{func.__qualname__}: {elapsed * 1000:.1f}ms"
            if logger:
                logger.log(msg)
            return result
        return wrapper
    return decorator


def safe_call(default=None):
    """Decorator: catch exceptions and return *default* instead."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                return default
        return wrapper
    return decorator