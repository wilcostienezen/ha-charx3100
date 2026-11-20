"""Sensors for the CHARX 3100."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CHARGING_STATES
from .coordinator import CharxConfigEntry
from .entity import CharxEntity
from .modbus import ChargingPointData


@dataclass(frozen=True, kw_only=True)
class CharxSensorDescription(SensorEntityDescription):
    """Describes a CHARX sensor."""

    value_fn: Callable[[ChargingPointData], float | int | str | None]


def _volt(key: str, fn: Callable[[ChargingPointData], float | None]) -> CharxSensorDescription:
    return CharxSensorDescription(
        key=key,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=fn,
    )


def _amp(key: str, fn: Callable[[ChargingPointData], float | None]) -> CharxSensorDescription:
    return CharxSensorDescription(
        key=key,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        value_fn=fn,
    )


SENSORS: tuple[CharxSensorDescription, ...] = (
    CharxSensorDescription(
        key="charging_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(CHARGING_STATES.values()),
        value_fn=lambda d: CHARGING_STATES.get(d.state_letter or ""),
    ),
    CharxSensorDescription(
        key="iec_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.iec_status or None,
    ),
    CharxSensorDescription(
        key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda d: d.active_power,
    ),
    CharxSensorDescription(
        key="reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.reactive_power,
    ),
    CharxSensorDescription(
        key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.apparent_power,
    ),
    CharxSensorDescription(
        key="energy_total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        # 0 is never a real meter reading; skip it so statistics do not reset.
        value_fn=lambda d: d.energy_total or None,
    ),
    CharxSensorDescription(
        key="energy_session",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: d.energy_session,
    ),
    _amp("current_l1", lambda d: d.current_l1),
    _amp("current_l2", lambda d: d.current_l2),
    _amp("current_l3", lambda d: d.current_l3),
    _volt("voltage_l1", lambda d: d.voltage_l1),
    _volt("voltage_l2", lambda d: d.voltage_l2),
    _volt("voltage_l3", lambda d: d.voltage_l3),
    CharxSensorDescription(
        key="charging_time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=2,
        value_fn=lambda d: d.charging_time,
    ),
    CharxSensorDescription(
        key="connection_time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=2,
        value_fn=lambda d: d.connection_time,
    ),
    CharxSensorDescription(
        key="pwm_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda d: d.pwm_current,
    ),
    CharxSensorDescription(
        key="pwm_duty_cycle",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.pwm_duty_cycle,
    ),
    CharxSensorDescription(
        key="cable_capacity",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.cable_capacity,
    ),
    CharxSensorDescription(
        key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: f"0x{d.error_code:08X}",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CharxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for every charging point."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CharxSensor(coordinator, number, description)
        for number in entry.runtime_data.charging_points
        for description in SENSORS
    )


class CharxSensor(CharxEntity, SensorEntity):
    """A CHARX charging point sensor."""

    entity_description: CharxSensorDescription

    def __init__(self, coordinator, number: int, description: CharxSensorDescription) -> None:
        super().__init__(coordinator, number, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | str | None:
        cp = self.cp
        return self.entity_description.value_fn(cp) if cp else None
