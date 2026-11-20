"""Maximum charging current for the CHARX 3100."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberMode, RestoreNumber
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MAX_CURRENT_LIMIT, DEFAULT_MAX_CURRENT_LIMIT, MIN_CURRENT
from .coordinator import CharxConfigEntry
from .entity import CharxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CharxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a max current number per charging point."""
    coordinator = entry.runtime_data.coordinator
    limit = entry.options.get(CONF_MAX_CURRENT_LIMIT, DEFAULT_MAX_CURRENT_LIMIT)
    async_add_entities(
        CharxMaxCurrentNumber(coordinator, number, limit)
        for number in entry.runtime_data.charging_points
    )


class CharxMaxCurrentNumber(CharxEntity, RestoreNumber):
    """Maximum charging current (register x301).

    The last value set from Home Assistant is remembered across restarts and
    written back when the controller reports something else (e.g. after a reset).
    """

    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = MIN_CURRENT
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, number: int, limit: int) -> None:
        super().__init__(coordinator, number, "max_current")
        self._attr_native_max_value = limit

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last and last.native_value is not None:
            amps = int(last.native_value)
            if MIN_CURRENT <= amps <= self._attr_native_max_value:
                self.coordinator.desired[self.number].max_current = amps

    @property
    def native_value(self) -> float | None:
        cp = self.cp
        return cp.max_current if cp else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_max_current(self.number, int(value))
