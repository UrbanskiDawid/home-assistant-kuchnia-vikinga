"""Config flow for Kuchnia Vikinga."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .api import VikingAuthError, VikingClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCHEMA = vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})


class KuchniaVikingaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()
            try:
                async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
                    client = VikingClient(
                        session, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                    )
                    await client.login()
                    await client.logout()
            except VikingAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Kuchnia Vikinga login failed")
                errors["base"] = "cannot_connect"
            if not errors:
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
