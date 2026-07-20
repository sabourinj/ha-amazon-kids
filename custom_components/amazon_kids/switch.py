"""Switch platform: one switch per child plus a master 'all' switch.

Semantics: switch ON = child is allowed (normal schedule). switch OFF =
child is paused (off-screen). Turning OFF pauses for the configured default
duration; use the amazon_kids.pause service for a per-call custom duration.

State is optimistic (tracks last command). See README.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .amazonkids import AmazonKidsClient, AmazonKidsError
from .const import (
    ATTR_MINUTES,
    CONF_CHILD_ID,
    CONF_CHILD_NAME,
    CONF_CHILDREN,
    CONF_DEFAULT_PAUSE_MINUTES,
    DEFAULT_PAUSE_MINUTES,
    DOMAIN,
    MAX_PAUSE_SECONDS,
    SERVICE_PAUSE,
    SERVICE_RESUME,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: AmazonKidsClient = hass.data[DOMAIN][entry.entry_id]
    children = entry.data[CONF_CHILDREN]
    default_minutes = entry.data.get(
        CONF_DEFAULT_PAUSE_MINUTES, DEFAULT_PAUSE_MINUTES
    )

    child_entities = [
        AmazonKidChildSwitch(
            client=client,
            entry_id=entry.entry_id,
            name=child[CONF_CHILD_NAME],
            directed_id=child[CONF_CHILD_ID],
            default_minutes=default_minutes,
        )
        for child in children
    ]
    master = AmazonKidMasterSwitch(
        client=client,
        entry_id=entry.entry_id,
        children=child_entities,
        default_minutes=default_minutes,
    )
    async_add_entities([*child_entities, master])

    # Register per-press configurable services.
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_PAUSE,
        {vol.Optional(ATTR_MINUTES): cv.positive_int},
        "async_service_pause",
    )
    platform.async_register_entity_service(
        SERVICE_RESUME, {}, "async_service_resume"
    )


class _BaseKidSwitch(SwitchEntity):
    """Shared optimistic-state switch behaviour."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    # ON = allowed. OFF = paused.
    _attr_assumed_state = True

    def __init__(
        self,
        client: AmazonKidsClient,
        entry_id: str,
        default_minutes: int,
    ) -> None:
        self._client = client
        self._entry_id = entry_id
        self._default_minutes = default_minutes
        self._is_on = True  # assume allowed until told otherwise

    @property
    def is_on(self) -> bool:
        return self._is_on

    # --- subclasses implement the id set they act on ---
    def _target_ids(self) -> list[str]:
        raise NotImplementedError

    async def _do_pause(self, minutes: int) -> None:
        seconds = min(minutes * 60, MAX_PAUSE_SECONDS)
        try:
            await self._client.pause(self._target_ids(), seconds)
        except AmazonKidsError as err:
            raise HomeAssistantError(f"Amazon Kids pause failed: {err}") from err
        self._set_optimistic(False)

    async def _do_resume(self) -> None:
        try:
            await self._client.resume(self._target_ids())
        except AmazonKidsError as err:
            raise HomeAssistantError(f"Amazon Kids resume failed: {err}") from err
        self._set_optimistic(True)

    @callback
    def _set_optimistic(self, is_on: bool) -> None:
        self._is_on = is_on
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allow (resume)."""
        await self._do_resume()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause for the default duration."""
        await self._do_pause(self._default_minutes)

    # Entity services
    async def async_service_pause(self, minutes: int | None = None) -> None:
        await self._do_pause(minutes or self._default_minutes)

    async def async_service_resume(self) -> None:
        await self._do_resume()


class AmazonKidChildSwitch(_BaseKidSwitch):
    """A single child's allow/pause switch."""

    def __init__(
        self,
        client: AmazonKidsClient,
        entry_id: str,
        name: str,
        directed_id: str,
        default_minutes: int,
    ) -> None:
        super().__init__(client, entry_id, default_minutes)
        self._directed_id = directed_id
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{directed_id}"

    def _target_ids(self) -> list[str]:
        return [self._directed_id]


class AmazonKidMasterSwitch(_BaseKidSwitch):
    """Master switch acting on all children at once (single API call)."""

    def __init__(
        self,
        client: AmazonKidsClient,
        entry_id: str,
        children: list[AmazonKidChildSwitch],
        default_minutes: int,
    ) -> None:
        super().__init__(client, entry_id, default_minutes)
        self._children = children
        self._attr_name = "All Kids"
        self._attr_unique_id = f"{entry_id}_all"

    def _target_ids(self) -> list[str]:
        return [c._directed_id for c in self._children]  # noqa: SLF001

    @callback
    def _set_optimistic(self, is_on: bool) -> None:
        super()._set_optimistic(is_on)
        # Reflect the bulk action on each child entity too.
        for child in self._children:
            child._set_optimistic(is_on)  # noqa: SLF001
