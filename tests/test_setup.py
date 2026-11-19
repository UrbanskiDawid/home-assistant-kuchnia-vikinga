"""Config flow + sensor, with the panel mocked."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kuchnia_vikinga.api import VikingAuthError
from custom_components.kuchnia_vikinga.const import DOMAIN

USER = {"username": "jan@example.com", "password": "secret"}
MEALS = [{"meal": "Obiad", "name": "Zupa pomidorowa", "ingredients": ["Pomidor", "Ryż"]}]
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

        # Same day: no new request to the panel.
        entity = hass.data["entity_components"]["sensor"].get_entity(state.entity_id)
        await entity._refresh()
        assert fetch.await_count == 1


async def test_flow_invalid_auth(enable_custom_integrations, hass):
    with patch(f"{CLIENT}.login", new=AsyncMock(side_effect=VikingAuthError)):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
