"""Charging release switch for the CHARX 3100."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import CharxConfigEntry
from .entity import CharxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CharxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a charging release switch per charging point."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CharxChargingReleaseSwitch(coordinator, number)
        for number in entry.runtime_data.charging_points
    )


class CharxChargingReleaseSwitch(CharxEntity, SwitchEntity, RestoreEntity):
    """Charging release (register x300).

    Requires release mode "Modbus" on the charging point in the CHARX web interface.
    The last state set from Home Assistant is remembered across restarts and
    written back when the controller reports something else (e.g. after a reset).
    """

    def __init__(self, coordinator, number: int) -> None:
        super().__init__(coordinator, number, "charging_release")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state in (STATE_ON, STATE_OFF):
            self.coordinator.desired[self.number].charging_release = last.state == STATE_ON

    @property
    def is_on(self) -> bool | None:
        cp = self.cp
        return cp.charging_release if cp else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_charging_release(self.number, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_charging_release(self.number, False)
