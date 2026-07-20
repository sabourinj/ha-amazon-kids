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

from homeassistant.helpers.entity import DeviceInfo

from .amazonkids import AmazonKidsClient
from .const import DOMAIN

MANUFACTURER = "Amazon (unofficial)"
MODEL = "Kids Parent Controls"


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
class PauseDuration:
    """Mutable pause-length setting (minutes) shared by a Pause button and
    its paired number entity -- the button reads whatever the number entity
    currently holds, instead of a fixed configured value."""

    minutes: int


@dataclass
class AmazonKidsRuntimeData:
    """Everything a config entry's platforms need: the API client plus state."""

    client: AmazonKidsClient
    children: dict[str, ChildPauseState]  # keyed by directed_id
    child_pause_minutes: dict[str, PauseDuration]  # keyed by directed_id
    all_pause_minutes: PauseDuration


def child_device_info(state: ChildPauseState) -> DeviceInfo:
    """Device grouping a child's entities so they're named after the child."""
    return DeviceInfo(
        identifiers={(DOMAIN, state.directed_id)},
        name=state.name,
        manufacturer=MANUFACTURER,
        model=MODEL,
    )


def all_kids_device_info(entry_id: str) -> DeviceInfo:
    """Device grouping the 'All Kids' entities for one config entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_all")},
        name="All Kids",
        manufacturer=MANUFACTURER,
        model=MODEL,
    )
