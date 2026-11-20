"""The CHARX 3100 integration (community project, not affiliated with Phoenix Contact)."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID
from .coordinator import CharxConfigEntry, CharxCoordinator, CharxRuntimeData
from .entity import controller_device_info
from .modbus import CharxConnectionError, CharxModbusClient

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: CharxConfigEntry) -> bool:
    """Set up a CHARX 3100 controller from a config entry."""
    client = CharxModbusClient(
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
        entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID),
    )
    try:
        count = await client.read_charging_point_count()
    except CharxConnectionError as err:
        client.close()
        raise ConfigEntryNotReady(str(err)) from err

    charging_points = list(range(1, count + 1))
    coordinator = CharxCoordinator(hass, entry, client, charging_points)
    entry.runtime_data = CharxRuntimeData(client, coordinator, charging_points)

    await coordinator.async_config_entry_first_refresh()

    # Register the controller first so the charging points can refer to it.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        **controller_device_info(entry.entry_id, entry.data[CONF_HOST]),
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CharxConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.client.close()
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: CharxConfigEntry) -> None:
    """Reload when the options change."""
    await hass.config_entries.async_reload(entry.entry_id)
