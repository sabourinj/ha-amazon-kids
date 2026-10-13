from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazon_kids.amazonkids import AmazonKidsAuthError
from custom_components.amazon_kids.const import DOMAIN

DATA = {
    "cookie": "old=1",
    "csrf_token": "oldtoken",
    "default_pause_minutes": 60,
    "children": [{"name": "Alex", "directed_id": "amzn1.account.ALEX"}],
}


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=dict(DATA), unique_id="amzn1.account.ALEX")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_reconfigure_keeps_children_and_entities(hass):
    entry = await _setup(hass)
    assert hass.states.get("button.alex_pause") is not None

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"cookie": " new=2 ", "csrf_token": "newtoken", "default_pause_minutes": 120},
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["cookie"] == "new=2"
    assert entry.data["csrf_token"] == "newtoken"
    assert entry.data["default_pause_minutes"] == 120
    assert entry.data["children"] == DATA["children"]
    assert hass.states.get("button.alex_pause") is not None  # same entity id after reload


async def test_auth_error_starts_reauth_and_reauth_updates_credentials(hass):
    entry = await _setup(hass)

    with patch(
        "custom_components.amazon_kids.amazonkids.AmazonKidsClient.pause",
        AsyncMock(side_effect=AmazonKidsAuthError("401")),
    ):
        with pytest.raises(HomeAssistantError, match="session expired"):
            await hass.services.async_call(
                "button", "press", {"entity_id": "button.alex_pause"}, blocking=True
            )
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1 and flows[0]["context"]["source"] == SOURCE_REAUTH

    result = await hass.config_entries.flow.async_configure(
        flows[0]["flow_id"], {"cookie": "fresh=3", "csrf_token": "freshtoken"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["cookie"] == "fresh=3"
    assert entry.data["default_pause_minutes"] == 60


async def test_pause_success_updates_status(hass):
    await _setup(hass)
    with patch(
        "custom_components.amazon_kids.amazonkids.AmazonKidsClient.pause", AsyncMock()
    ) as pause:
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.alex_pause"}, blocking=True
        )
    pause.assert_awaited_once_with(["amzn1.account.ALEX"], 3600)
    assert hass.states.get("sensor.alex_status").state == "paused"


async def test_user_flow_creates_entry_with_children(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"cookie": "a=1", "csrf_token": "tok", "default_pause_minutes": 30}
    )
    assert result["step_id"] == "child"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Alex", "directed_id": "id1", "add_another": True}
    )
    assert result["step_id"] == "child"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Sam", "directed_id": "id1", "add_another": False}
    )
    assert result["errors"] == {"base": "child_duplicate"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Sam", "directed_id": "id2", "add_another": False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert [c["name"] for c in result["data"]["children"]] == ["Alex", "Sam"]
