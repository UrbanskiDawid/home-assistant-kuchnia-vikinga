"""Sensor: state = number of meals today, attribute `meals` = [{meal, name, kcal, ingredients, vote}].

The panel is polled hourly (5 minutes past), and again right after a vote, so
votes cast in the panel itself show up too. Votes are stored on the panel only.
"""

from __future__ import annotations

import logging
from datetime import date

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .api import VikingClient, VikingError
from .const import DOMAIN, TIME_ZONE

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
        return {"date": self._day.isoformat(), "meals": self._meals}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_time_change(self.hass, self._hourly, minute=5, second=0)
        )
        self.hass.data[DOMAIN][self._attr_unique_id] = self
        self.async_on_remove(lambda: self.hass.data[DOMAIN].pop(self._attr_unique_id, None))
        self.hass.async_create_task(self._refresh())

    @callback
    def _hourly(self, _now) -> None:
        self.hass.async_create_task(self._refresh())

    async def async_vote(self, name: str, vote: str) -> bool:
        """Push a vote for today's meal `name`; False if this sensor has no such meal."""
        meal = next((m for m in self._meals if m["name"] == name), None)
        if meal is None:
            return False
        try:
            await self._client.set_vote(meal["id"], vote)
        except VikingError as err:
            raise HomeAssistantError(f"Saving the vote failed: {err}") from err
        await self._refresh()
        return True

    async def _refresh(self) -> None:
        today = dt_util.now(dt_util.get_time_zone(TIME_ZONE)).date()
        try:
            meals = await self._client.todays_meals(today)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Fetching today's meals failed, will retry next hour: %s", err)
            return
        self._day = today
        self._meals = meals
        self._attr_native_value = len(meals)
        self.async_write_ha_state()
