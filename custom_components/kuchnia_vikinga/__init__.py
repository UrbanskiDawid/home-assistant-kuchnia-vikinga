"""Kuchnia Vikinga: today's meals and their ingredients as one sensor, with 👍/👎 votes."""

from __future__ import annotations

from pathlib import Path

import aiohttp
import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import VikingClient
from .const import CARD_URL, DOMAIN, VOTES

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

VOTE_SCHEMA = vol.Schema(
    {vol.Required(CONF_NAME): cv.string, vol.Required("vote"): vol.In(VOTES)}
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[DOMAIN] = {}  # entry_id -> sensor; votes live on the vendor's server

    async def vote(call: ServiceCall) -> None:
        """Send a 👍/👎 for a dish to the panel, then re-pull so the sensor shows it."""
        name = call.data[CONF_NAME].strip()
        for sensor in list(hass.data[DOMAIN].values()):
            if await sensor.async_vote(name, call.data["vote"]):
                return
        raise ServiceValidationError(f"No meal named '{name}' in today's menu")

    hass.services.async_register(DOMAIN, "vote", vote, schema=VOTE_SCHEMA)

    # The dashboard card ships with the integration, no separate download needed.
    if hass.http is not None and "frontend" in hass.config.components:
        version = (await async_get_integration(hass, DOMAIN)).version
        card = Path(__file__).parent / "www" / "kuchnia-vikinga-card.js"
        await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(card), False)])
        add_extra_js_url(hass, f"{CARD_URL}?v={version}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Own session: the panel's login cookies must not leak into HA's shared session.
    session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
    entry.async_on_unload(session.close)
    entry.runtime_data = VikingClient(
        session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
