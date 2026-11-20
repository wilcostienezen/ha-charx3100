"""Binary sensors for the CHARX 3100."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CharxConfigEntry
from .entity import CharxEntity
from .modbus import ChargingPointData


@dataclass(frozen=True, kw_only=True)
class CharxBinaryDescription(BinarySensorEntityDescription):
    """Describes a CHARX binary sensor."""

    value_fn: Callable[[ChargingPointData], bool | None]


BINARY_SENSORS: tuple[CharxBinaryDescription, ...] = (
    CharxBinaryDescription(
        key="vehicle_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=lambda d: d.state_letter in ("B", "C", "D") if d.state_letter else None,
    ),
    CharxBinaryDescription(
        key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda d: d.state_letter in ("C", "D") if d.state_letter else None,
    ),
    CharxBinaryDescription(
        key="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.error_code != 0 or d.state_letter == "E",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CharxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors for every charging point."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CharxBinarySensor(coordinator, number, description)
        for number in entry.runtime_data.charging_points
        for description in BINARY_SENSORS
    )


class CharxBinarySensor(CharxEntity, BinarySensorEntity):
    """A CHARX charging point binary sensor."""

    entity_description: CharxBinaryDescription

    def __init__(self, coordinator, number: int, description: CharxBinaryDescription) -> None:
        super().__init__(coordinator, number, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        cp = self.cp
        return self.entity_description.value_fn(cp) if cp else None
