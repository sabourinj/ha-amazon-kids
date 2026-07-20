"""Config flow for Amazon Kids."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

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

CONF_ADD_ANOTHER = "add_another"

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_COOKIE): str,
        vol.Required(CONF_CSRF_TOKEN): str,
        vol.Optional(
            CONF_DEFAULT_PAUSE_MINUTES, default=DEFAULT_PAUSE_MINUTES
        ): int,
    }
)

STEP_CHILD_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CHILD_NAME): str,
        vol.Required(CONF_CHILD_ID): str,
        vol.Optional(CONF_ADD_ANOTHER, default=False): bool,
    }
)


class AmazonKidsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow.

    Credentials are collected once, then children are added one at a time
    (instead of a single JSON blob) so a mistake in one child doesn't
    invalidate the whole form and each child's directedId can be explained
    inline, right where it's needed.
    """

    VERSION = 1

    def __init__(self) -> None:
        self._entry_data: dict[str, Any] = {}
        self._children: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._entry_data = {
                CONF_COOKIE: user_input[CONF_COOKIE].strip(),
                CONF_CSRF_TOKEN: user_input[CONF_CSRF_TOKEN].strip(),
                CONF_DEFAULT_PAUSE_MINUTES: user_input[CONF_DEFAULT_PAUSE_MINUTES],
            }
            return await self.async_step_child()

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA)

    async def async_step_child(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_CHILD_NAME].strip()
            directed_id = user_input[CONF_CHILD_ID].strip()
            if not name or not directed_id:
                errors["base"] = "child_incomplete"
            elif any(
                child[CONF_CHILD_ID] == directed_id for child in self._children
            ):
                errors["base"] = "child_duplicate"
            else:
                self._children.append(
                    {CONF_CHILD_NAME: name, CONF_CHILD_ID: directed_id}
                )
                if user_input[CONF_ADD_ANOTHER]:
                    return await self.async_step_child()
                return await self._async_finish()

        return self.async_show_form(
            step_id="child",
            data_schema=STEP_CHILD_SCHEMA,
            errors=errors,
            description_placeholders={
                "added": ", ".join(
                    child[CONF_CHILD_NAME] for child in self._children
                )
                or "none yet"
            },
        )

    async def _async_finish(self) -> ConfigFlowResult:
        unique_id = "_".join(
            sorted(child[CONF_CHILD_ID] for child in self._children)
        )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Amazon Kids",
            data={**self._entry_data, CONF_CHILDREN: self._children},
        )
