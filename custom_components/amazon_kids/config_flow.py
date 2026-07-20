"""Config flow for Amazon Kids."""

from __future__ import annotations

import json
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

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_COOKIE): str,
        vol.Required(CONF_CSRF_TOKEN): str,
        # Children entered as JSON: [{"name": "Alex", "directed_id": "amzn1.account...."}]
        vol.Required(CONF_CHILDREN): str,
        vol.Optional(
            CONF_DEFAULT_PAUSE_MINUTES, default=DEFAULT_PAUSE_MINUTES
        ): int,
    }
)


def _validate_children(raw: str) -> list[dict[str, str]]:
    """Parse and validate the children JSON blob."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        raise ValueError("children_not_json") from err
    if not isinstance(parsed, list) or not parsed:
        raise ValueError("children_empty")
    result: list[dict[str, str]] = []
    for item in parsed:
        if (
            not isinstance(item, dict)
            or CONF_CHILD_NAME not in item
            or CONF_CHILD_ID not in item
        ):
            raise ValueError("children_shape")
        result.append(
            {
                CONF_CHILD_NAME: str(item[CONF_CHILD_NAME]),
                CONF_CHILD_ID: str(item[CONF_CHILD_ID]),
            }
        )
    return result


class AmazonKidsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                children = _validate_children(user_input[CONF_CHILDREN])
            except ValueError as err:
                errors["base"] = str(err)
            else:
                data = {
                    CONF_COOKIE: user_input[CONF_COOKIE].strip(),
                    CONF_CSRF_TOKEN: user_input[CONF_CSRF_TOKEN].strip(),
                    CONF_CHILDREN: children,
                    CONF_DEFAULT_PAUSE_MINUTES: user_input[
                        CONF_DEFAULT_PAUSE_MINUTES
                    ],
                }
                return self.async_create_entry(
                    title="Amazon Kids", data=data
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
