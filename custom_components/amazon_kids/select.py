"""Select platform: pick a preset pause duration, per child and for All Kids.

Home Assistant buttons can't prompt for input when pressed, and dragging a
number slider across a 1-1440 minute range is fiddly. Common durations as
tap-to-pick presets fit how this is actually used; the amazon_kids.pause
service's `minutes` field remains for one-off custom durations that don't
match a preset (e.g. from automations).
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .runtime import (
    AmazonKidsRuntimeData,
    PauseDuration,
    all_kids_device_info,
    child_device_info,
)

PRESET_MINUTES = {
    "15 minutes": 15,
    "30 minutes": 30,
    "1 hour": 60,
    "2 hours": 120,
    "4 hours": 240,
    "8 hours": 480,
    "24 hours": 1440,
}


def _closest_preset(minutes: int) -> str:
    """Map an arbitrary minute value (e.g. a configured default) to whichever
    preset is numerically closest, so the select always has a valid option
    selected even if it doesn't exactly match one."""
    return min(PRESET_MINUTES, key=lambda option: abs(PRESET_MINUTES[option] - minutes))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: AmazonKidsRuntimeData = hass.data[DOMAIN][entry.entry_id]
    states = list(runtime.children.values())

    entities = [
        AmazonKidPauseDurationSelect(
            unique_id=f"{entry.entry_id}_{state.directed_id}_pause_duration",
            device_info=child_device_info(state),
            duration=runtime.child_pause_minutes[state.directed_id],
        )
        for state in states
    ]
    if states:
        entities.append(
            AmazonKidPauseDurationSelect(
                unique_id=f"{entry.entry_id}_all_pause_duration",
                device_info=all_kids_device_info(entry.entry_id),
                duration=runtime.all_pause_minutes,
            )
        )

    async_add_entities(entities)


class AmazonKidPauseDurationSelect(SelectEntity, RestoreEntity):
    """Which preset the paired Pause button pauses for, until changed again."""

    _attr_has_entity_name = True
    _attr_name = "Pause Duration"
    _attr_icon = "mdi:timer-outline"
    _attr_options = list(PRESET_MINUTES)

    def __init__(
        self, unique_id: str, device_info: DeviceInfo, duration: PauseDuration
    ) -> None:
        self._duration = duration
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in PRESET_MINUTES:
            self._duration.minutes = PRESET_MINUTES[last_state.state]

    @property
    def current_option(self) -> str:
        return _closest_preset(self._duration.minutes)

    async def async_select_option(self, option: str) -> None:
        self._duration.minutes = PRESET_MINUTES[option]
        self.async_write_ha_state()
