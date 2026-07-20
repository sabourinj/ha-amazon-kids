"""Number platform: adjustable pause duration, per child and for All Kids.

Home Assistant buttons can't prompt for input when pressed. Instead, each
Pause button (see button.py) reads the current value of its paired "Pause
Duration" number entity here -- set it once, or dial it up/down right before
pressing Pause. Falls back to the default configured at setup, and persists
across restarts via RestoreEntity.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, MAX_PAUSE_SECONDS
from .runtime import (
    AmazonKidsRuntimeData,
    PauseDuration,
    all_kids_device_info,
    child_device_info,
)

MAX_MINUTES = MAX_PAUSE_SECONDS // 60


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: AmazonKidsRuntimeData = hass.data[DOMAIN][entry.entry_id]
    states = list(runtime.children.values())

    entities = [
        AmazonKidPauseDurationNumber(
            unique_id=f"{entry.entry_id}_{state.directed_id}_pause_minutes",
            device_info=child_device_info(state),
            duration=runtime.child_pause_minutes[state.directed_id],
        )
        for state in states
    ]
    if states:
        entities.append(
            AmazonKidPauseDurationNumber(
                unique_id=f"{entry.entry_id}_all_pause_minutes",
                device_info=all_kids_device_info(entry.entry_id),
                duration=runtime.all_pause_minutes,
            )
        )

    async_add_entities(entities)


class AmazonKidPauseDurationNumber(NumberEntity, RestoreEntity):
    """How long the paired Pause button pauses for, until changed again."""

    _attr_has_entity_name = True
    _attr_name = "Pause Duration"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 1
    _attr_native_max_value = MAX_MINUTES
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    def __init__(
        self, unique_id: str, device_info: DeviceInfo, duration: PauseDuration
    ) -> None:
        self._duration = duration
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in (None, "unknown", "unavailable"):
            return
        try:
            restored = int(float(last_state.state))
        except ValueError:
            return
        self._duration.minutes = max(1, min(restored, MAX_MINUTES))

    @property
    def native_value(self) -> float:
        return self._duration.minutes

    async def async_set_native_value(self, value: float) -> None:
        self._duration.minutes = int(value)
        self.async_write_ha_state()
