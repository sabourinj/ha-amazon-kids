"""Shared per-entry runtime state.

Amazon exposes no endpoint to read whether a child is currently paused, so
there is no ground truth to poll. Instead, button presses update a
``ChildPauseState`` here, and sensor entities subscribe to it to reflect the
last command this integration issued.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from .amazonkids import AmazonKidsClient


@dataclass
class ChildPauseState:
    """Locally-tracked pause status for one child."""

    name: str
    directed_id: str
    is_paused: bool = False
    resumes_at: datetime | None = None
    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def set_paused(self, resumes_at: datetime) -> None:
        self.is_paused = True
        self.resumes_at = resumes_at
        self._notify()

    def set_allowed(self) -> None:
        self.is_paused = False
        self.resumes_at = None
        self._notify()

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()


@dataclass
class AmazonKidsRuntimeData:
    """Everything a config entry's platforms need: the API client plus state."""

    client: AmazonKidsClient
    children: dict[str, ChildPauseState]  # keyed by directed_id
