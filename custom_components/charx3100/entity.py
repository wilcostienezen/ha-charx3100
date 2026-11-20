"""Base entity for the CHARX 3100."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CharxCoordinator
from .modbus import ChargingPointData


class CharxEntity(CoordinatorEntity[CharxCoordinator]):
    """An entity that belongs to one charging point."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CharxCoordinator, number: int, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self.number = number
        self._attr_unique_id = f"{entry.entry_id}_{number}_{key}"
        self._attr_translation_key = key
        host = entry.data[CONF_HOST]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{number}")},
            name=f"Charging point {number}",
            manufacturer="Phoenix Contact",
            model="CHARX control modular charging point",
            via_device=(DOMAIN, entry.entry_id),
            configuration_url=f"https://{host}/",
        )

    @property
    def cp(self) -> ChargingPointData | None:
        """Return the latest data of this charging point."""
        data = self.coordinator.data
        return data.get(self.number) if data else None

    @property
    def available(self) -> bool:
        """Available while the last poll succeeded and returned this point."""
        return super().available and self.cp is not None


def controller_device_info(entry_id: str, host: str) -> DeviceInfo:
    """Device info for the controller itself (parent of the charging points)."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=f"CHARX 3100 ({host})",
        manufacturer="Phoenix Contact",
        model="CHARX SEC-3100",
        configuration_url=f"https://{host}/",
    )
