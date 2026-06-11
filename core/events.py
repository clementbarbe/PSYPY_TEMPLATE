"""
Lightweight event bus for decoupled communication.

Components can publish events (e.g., 'trial_end', 'block_start')
without knowing who listens. Useful for optional plugins
(eye-tracker messages, live plotting, QC hooks).

Usage:
    bus = EventBus()
    bus.subscribe('trial_end', my_callback)
    bus.publish('trial_end', record=record)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Any


class EventBus:
    """Thread-unsafe (single-thread PsychoPy) pub/sub event bus."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """Register *callback* to fire when *event_name* is published."""
        self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """Remove a previously registered callback."""
        try:
            self._subscribers[event_name].remove(callback)
        except ValueError:
            pass

    def publish(self, event_name: str, **kwargs: Any) -> None:
        """Fire all callbacks registered for *event_name*."""
        for cb in self._subscribers.get(event_name, []):
            try:
                cb(**kwargs)
            except Exception:
                pass  # Never let a subscriber crash the experiment

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscribers.clear()