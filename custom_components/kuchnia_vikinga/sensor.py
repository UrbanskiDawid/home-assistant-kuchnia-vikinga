"""Sensor: state = number of meals today, attribute `meals` = [{meal, name, kcal, ingredients, vote}].

The panel is asked once a day. After a successful fetch nothing is requested
until the date changes; on failure it tries again at the next full hour.
"""

from __future__ import annotations

import logging
from datetime import date

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .api import VikingClient
from .const import DOMAIN, SIGNAL_VOTES, TIME_ZONE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([TodayMealsSensor(entry.runtime_data, entry.entry_id)])


class TodayMealsSensor(SensorEntity):
    _attr_name = "Kuchnia Vikinga dzisiaj"
    _attr_icon = "mdi:food"
    _attr_native_unit_of_measurement = "meals"
    _attr_should_poll = False
    _unrecorded_attributes = frozenset({"meals"})

    def __init__(self, client: VikingClient, entry_id: str) -> None:
        self._client = client
        self._attr_unique_id = f"{entry_id}_today"
        self._day: date | None = None  # day of the last successful fetch
        self._meals: list[dict] = []

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._day is None:
            return None
        votes = self.hass.data[DOMAIN]
        return {
            "date": self._day.isoformat(),
            "meals": [{**m, "vote": votes.get(m["name"])} for m in self._meals],
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_time_change(self.hass, self._hourly, minute=5, second=0)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_VOTES, self.async_write_ha_state)
        )
        self.hass.async_create_task(self._refresh())

    @callback
    def _hourly(self, _now) -> None:
        self.hass.async_create_task(self._refresh())

    async def _refresh(self) -> None:
        today = dt_util.now(dt_util.get_time_zone(TIME_ZONE)).date()
        if self._day == today:
            return
        try:
            meals = await self._client.todays_meals(today)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Fetching today's meals failed, will retry in an hour: %s", err)
            return
        self._day = today
        self._meals = meals
        self._attr_native_value = len(meals)
        self.async_write_ha_state()
