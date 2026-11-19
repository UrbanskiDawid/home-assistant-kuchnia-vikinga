"""Kuchnia Vikinga: today's meals and their ingredients as one sensor."""

from __future__ import annotations

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .api import VikingClient


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
