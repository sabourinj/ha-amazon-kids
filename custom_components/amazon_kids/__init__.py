"""Amazon Kids Parent Controls integration for Home Assistant.

Unofficial. Uses the private parents.amazon.com endpoints. State is optimistic:
Home Assistant tracks the last command it issued rather than polling Amazon,
because no readable "currently paused" endpoint has been identified.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .amazonkids import AmazonKidsClient
from .const import (
    CONF_CHILD_ID,
    CONF_CHILD_NAME,
    CONF_CHILDREN,
    CONF_COOKIE,
    CONF_CSRF_TOKEN,
    CONF_DEFAULT_PAUSE_MINUTES,
    DEFAULT_PAUSE_MINUTES,
    DOMAIN,
)
from .runtime import AmazonKidsRuntimeData, ChildPauseState, PauseDuration

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.NUMBER, Platform.SENSOR]


def _parse_cookie_header(raw: str) -> dict[str, str]:
    """Turn a raw 'a=1; b=2' cookie header into a dict."""
    cookies: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Amazon Kids from a config entry."""
    session = async_get_clientsession(hass)
    cookies = _parse_cookie_header(entry.data[CONF_COOKIE])
    client = AmazonKidsClient(
        cookies=cookies,
        csrf_token=entry.data[CONF_CSRF_TOKEN],
        session=session,
    )

    children = {
        child[CONF_CHILD_ID]: ChildPauseState(
            name=child[CONF_CHILD_NAME], directed_id=child[CONF_CHILD_ID]
        )
        for child in entry.data[CONF_CHILDREN]
    }
    default_minutes = entry.data.get(
        CONF_DEFAULT_PAUSE_MINUTES, DEFAULT_PAUSE_MINUTES
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = AmazonKidsRuntimeData(
        client=client,
        children=children,
        child_pause_minutes={
            directed_id: PauseDuration(minutes=default_minutes)
            for directed_id in children
        },
        all_pause_minutes=PauseDuration(minutes=default_minutes),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
