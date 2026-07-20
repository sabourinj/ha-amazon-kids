"""Sensor platform: locally-tracked pause status.

These reflect the last command this integration issued, not verified state
read from Amazon -- see README for why. Use the button platform to act;
use these to see what was last commanded.
"""

from __future__ import annotations

from typing import Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .runtime import AmazonKidsRuntimeData, ChildPauseState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: AmazonKidsRuntimeData = hass.data[DOMAIN][entry.entry_id]
    states = list(runtime.children.values())

    child_sensors = [
        AmazonKidStatusSensor(entry.entry_id, state) for state in states
    ]
    all_sensor = AmazonKidsAllStatusSensor(entry.entry_id, states)
    async_add_entities([*child_sensors, all_sensor])


class AmazonKidStatusSensor(SensorEntity):
    """Whether one child is allowed or paused, as last commanded."""

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:account-clock"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["allowed", "paused"]

    def __init__(self, entry_id: str, state: ChildPauseState) -> None:
        self._state_obj = state
        self._attr_unique_id = f"{entry_id}_{state.directed_id}_status"
        self._remove_listener: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        self._remove_listener = self._state_obj.add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()

    @property
    def native_value(self) -> str:
        return "paused" if self._state_obj.is_paused else "allowed"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "resumes_at": (
                self._state_obj.resumes_at.isoformat()
                if self._state_obj.resumes_at
                else None
            ),
        }


class AmazonKidsAllStatusSensor(SensorEntity):
    """Aggregate status across all children on this config entry."""

    _attr_has_entity_name = True
    _attr_name = "All Kids Status"
    _attr_icon = "mdi:account-multiple-check"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["all_allowed", "all_paused", "mixed"]

    def __init__(self, entry_id: str, states: list[ChildPauseState]) -> None:
        self._states = states
        self._attr_unique_id = f"{entry_id}_all_status"
        self._removers: list[Callable[[], None]] = []

    async def async_added_to_hass(self) -> None:
        self._removers = [
            state.add_listener(self.async_write_ha_state) for state in self._states
        ]

    async def async_will_remove_from_hass(self) -> None:
        for remove in self._removers:
            remove()

    @property
    def native_value(self) -> str:
        paused = sum(1 for state in self._states if state.is_paused)
        if paused == 0:
            return "all_allowed"
        if paused == len(self._states):
            return "all_paused"
        return "mixed"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "paused_children": [s.name for s in self._states if s.is_paused],
            "total_children": len(self._states),
        }
