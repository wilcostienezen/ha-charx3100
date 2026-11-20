"""Data update coordinator for the CHARX 3100."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_RESTORE_ON_RESET,
    CONF_SCAN_INTERVAL,
    DEFAULT_RESTORE_ON_RESET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .modbus import ChargingPointData, CharxConnectionError, CharxModbusClient

_LOGGER = logging.getLogger(__name__)


@dataclass
class DesiredState:
    """What Home Assistant wants a charging point to be set to."""

    charging_release: bool | None = None
    max_current: int | None = None


@dataclass
class CharxRuntimeData:
    """Objects stored on the config entry."""

    client: CharxModbusClient
    coordinator: CharxCoordinator
    charging_points: list[int] = field(default_factory=list)


type CharxConfigEntry = ConfigEntry[CharxRuntimeData]


class CharxCoordinator(DataUpdateCoordinator[dict[int, ChargingPointData]]):
    """Polls all charging points and re-applies settings after a controller reset."""

    config_entry: CharxConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CharxConfigEntry,
        client: CharxModbusClient,
        charging_points: list[int],
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {client.host}",
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.charging_points = charging_points
        self.desired: dict[int, DesiredState] = {n: DesiredState() for n in charging_points}

    @property
    def restore_on_reset(self) -> bool:
        """Return whether settings are written back when the controller differs."""
        return self.config_entry.options.get(CONF_RESTORE_ON_RESET, DEFAULT_RESTORE_ON_RESET)

    async def _async_update_data(self) -> dict[int, ChargingPointData]:
        data: dict[int, ChargingPointData] = {}
        try:
            for number in self.charging_points:
                cp = await self.client.read_charging_point(number)
                if self.restore_on_reset:
                    cp = await self._async_restore(cp)
                data[number] = cp
        except CharxConnectionError as err:
            raise UpdateFailed(str(err)) from err
        return data

    async def _async_restore(self, cp: ChargingPointData) -> ChargingPointData:
        """Write back the desired values if the controller reports something else.

        Only writes when there is a difference, so the controller is not loaded
        with redundant writes.
        """
        want = self.desired.get(cp.number)
        if want is None:
            return cp
        if want.max_current is not None and cp.max_current != want.max_current:
            _LOGGER.info(
                "Charging point %s: max current is %s A, restoring %s A",
                cp.number, cp.max_current, want.max_current,
            )
            await self.client.write_max_current(cp.number, want.max_current)
            cp.max_current = want.max_current
        if want.charging_release is not None and cp.charging_release != want.charging_release:
            _LOGGER.info(
                "Charging point %s: charging release is %s, restoring %s",
                cp.number, cp.charging_release, want.charging_release,
            )
            await self.client.write_charging_release(cp.number, want.charging_release)
            cp.charging_release = want.charging_release
        return cp

    async def async_set_charging_release(self, number: int, enabled: bool) -> None:
        """Set the charging release of a charging point."""
        self.desired[number].charging_release = enabled
        try:
            await self.client.write_charging_release(number, enabled)
        except CharxConnectionError as err:
            raise HomeAssistantError(f"Could not set charging release: {err}") from err
        if self.data and number in self.data:
            self.data[number].charging_release = enabled
            self.async_update_listeners()

    async def async_set_max_current(self, number: int, amps: int) -> None:
        """Set the maximum charging current of a charging point."""
        self.desired[number].max_current = amps
        try:
            await self.client.write_max_current(number, amps)
        except CharxConnectionError as err:
            raise HomeAssistantError(f"Could not set max current: {err}") from err
        if self.data and number in self.data:
            self.data[number].max_current = amps
            self.async_update_listeners()
