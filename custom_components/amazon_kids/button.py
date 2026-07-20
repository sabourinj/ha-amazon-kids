"""Button platform: pause/resume actions, per child and for All Kids.

A button only fires a command -- it makes no claim about current state,
which matches this integration's actual capability (there is no read-back
from Amazon). See the sensor platform for the locally-tracked status this
button's presses drive.
"""

from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .amazonkids import AmazonKidsClient, AmazonKidsError
from .const import (
    ATTR_MINUTES,
    DOMAIN,
    MAX_PAUSE_SECONDS,
    SERVICE_PAUSE,
    SERVICE_RESUME,
)
from .runtime import (
    AmazonKidsRuntimeData,
    ChildPauseState,
    PauseDuration,
    all_kids_device_info,
    child_device_info,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: AmazonKidsRuntimeData = hass.data[DOMAIN][entry.entry_id]
    states = list(runtime.children.values())

    entities: list[ButtonEntity] = []
    for state in states:
        duration = runtime.child_pause_minutes[state.directed_id]
        entities.append(
            AmazonKidPauseButton(entry.entry_id, runtime.client, [state], duration)
        )
        entities.append(AmazonKidResumeButton(entry.entry_id, runtime.client, [state]))

    if states:
        entities.append(
            AmazonKidPauseButton(
                entry.entry_id,
                runtime.client,
                states,
                runtime.all_pause_minutes,
                is_all=True,
            )
        )
        entities.append(
            AmazonKidResumeButton(entry.entry_id, runtime.client, states, is_all=True)
        )

    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_PAUSE,
        {vol.Optional(ATTR_MINUTES): cv.positive_int},
        "async_service_pause",
    )
    platform.async_register_entity_service(SERVICE_RESUME, {}, "async_service_resume")


class _BaseKidButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        client: AmazonKidsClient,
        states: list[ChildPauseState],
        suffix: str,
        is_all: bool,
    ) -> None:
        self._client = client
        self._states = states
        target = "all" if is_all else states[0].directed_id
        self._attr_unique_id = f"{entry_id}_{target}_{suffix}"
        self._attr_device_info = (
            all_kids_device_info(entry_id) if is_all else child_device_info(states[0])
        )

    def _target_ids(self) -> list[str]:
        return [state.directed_id for state in self._states]


class AmazonKidPauseButton(_BaseKidButton):
    """Pause for the paired Pause Duration number entity's current value
    (or a custom one-off duration via the amazon_kids.pause service)."""

    _attr_icon = "mdi:pause-circle"

    def __init__(
        self,
        entry_id: str,
        client: AmazonKidsClient,
        states: list[ChildPauseState],
        duration: PauseDuration,
        is_all: bool = False,
    ) -> None:
        super().__init__(entry_id, client, states, "pause", is_all)
        self._duration = duration
        self._attr_name = "Pause"

    async def async_press(self) -> None:
        await self.async_service_pause()

    async def async_service_pause(self, minutes: int | None = None) -> None:
        seconds = min(
            (minutes if minutes is not None else self._duration.minutes) * 60,
            MAX_PAUSE_SECONDS,
        )
        try:
            await self._client.pause(self._target_ids(), seconds)
        except AmazonKidsError as err:
            raise HomeAssistantError(f"Amazon Kids pause failed: {err}") from err
        resumes_at = dt_util.utcnow() + timedelta(seconds=seconds)
        for state in self._states:
            state.set_paused(resumes_at)


class AmazonKidResumeButton(_BaseKidButton):
    """Clear the off-screen override immediately."""

    _attr_icon = "mdi:play-circle"

    def __init__(
        self,
        entry_id: str,
        client: AmazonKidsClient,
        states: list[ChildPauseState],
        is_all: bool = False,
    ) -> None:
        super().__init__(entry_id, client, states, "resume", is_all)
        self._attr_name = "Resume"

    async def async_press(self) -> None:
        await self.async_service_resume()

    async def async_service_resume(self) -> None:
        try:
            await self._client.resume(self._target_ids())
        except AmazonKidsError as err:
            raise HomeAssistantError(f"Amazon Kids resume failed: {err}") from err
        for state in self._states:
            state.set_allowed()
