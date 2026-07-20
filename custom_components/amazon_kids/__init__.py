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
from .const import CONF_COOKIE, CONF_CSRF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]


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

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

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
