"""Config flow + sensor, with the panel mocked."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError

from custom_components.kuchnia_vikinga.api import VikingAuthError
from custom_components.kuchnia_vikinga.const import DOMAIN

USER = {"username": "jan@example.com", "password": "secret"}
MEALS = [{"id": 5, "meal": "Obiad", "name": "Zupa pomidorowa", "ingredients": ["Pomidor", "Ryż"], "vote": None}]
CLIENT = "custom_components.kuchnia_vikinga.api.VikingClient"


async def test_flow_and_sensor(enable_custom_integrations, hass):
    with patch(f"{CLIENT}.login", new=AsyncMock()), patch(
        f"{CLIENT}.logout", new=AsyncMock()
    ), patch(f"{CLIENT}.todays_meals", new=AsyncMock(return_value=MEALS)) as fetch:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER)
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()

        state = hass.states.get("sensor.kuchnia_vikinga_dzisiaj")
        assert state.state == "1"
        assert state.attributes["meals"] == MEALS
        assert fetch.await_count == 1

        # Hourly refresh re-pulls, so votes cast in the panel show up.
        entity = hass.data["entity_components"]["sensor"].get_entity(state.entity_id)
        await entity._refresh()
        assert fetch.await_count == 2


async def test_flow_invalid_auth(enable_custom_integrations, hass):
    with patch(f"{CLIENT}.login", new=AsyncMock(side_effect=VikingAuthError)):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_vote_goes_to_panel(enable_custom_integrations, hass, hass_storage):
    voted = [{**MEALS[0], "vote": "up"}]
    with patch(f"{CLIENT}.login", new=AsyncMock()), patch(
        f"{CLIENT}.logout", new=AsyncMock()
    ), patch(f"{CLIENT}.todays_meals", new=AsyncMock(side_effect=[MEALS, voted])), patch(
        f"{CLIENT}.set_vote", new=AsyncMock()
    ) as push:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(result["flow_id"], USER)
        await hass.async_block_till_done()

        await hass.services.async_call(
            DOMAIN, "vote", {"name": "Zupa pomidorowa", "vote": "up"}, blocking=True
        )
        push.assert_awaited_once_with(5, "up")
        state = hass.states.get("sensor.kuchnia_vikinga_dzisiaj")
        assert state.attributes["meals"][0]["vote"] == "up"
        assert "kuchnia_vikinga.votes" not in hass_storage  # nothing stored locally

        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN, "vote", {"name": "Nieznane", "vote": "up"}, blocking=True
            )
