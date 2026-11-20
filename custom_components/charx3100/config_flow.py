"""Config flow for the CHARX 3100."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    ABSOLUTE_MAX_CURRENT,
    CONF_MAX_CURRENT_LIMIT,
    CONF_RESTORE_ON_RESET,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_MAX_CURRENT_LIMIT,
    DEFAULT_PORT,
    DEFAULT_RESTORE_ON_RESET,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_CURRENT,
    MIN_SCAN_INTERVAL,
)
from .modbus import CharxConnectionError, CharxModbusClient


async def _async_count_points(host: str, port: int, unit_id: int) -> int:
    client = CharxModbusClient(host, port, unit_id)
    try:
        return await client.read_charging_point_count()
    finally:
        client.close()


class CharxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a CHARX 3100 controller."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            try:
                count = await _async_count_points(
                    host, user_input[CONF_PORT], user_input[CONF_UNIT_ID]
                )
            except CharxConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"CHARX 3100 ({host})",
                    data={**user_input, CONF_HOST: host},
                    description_placeholders={"count": str(count)},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=247)
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> CharxOptionsFlow:
        return CharxOptionsFlow()


class CharxOptionsFlow(OptionsFlow):
    """Options: poll interval, current limit, restore behaviour."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=1,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_MAX_CURRENT_LIMIT,
                    default=opts.get(CONF_MAX_CURRENT_LIMIT, DEFAULT_MAX_CURRENT_LIMIT),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_CURRENT,
                        max=ABSOLUTE_MAX_CURRENT,
                        step=1,
                        unit_of_measurement="A",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_RESTORE_ON_RESET,
                    default=opts.get(CONF_RESTORE_ON_RESET, DEFAULT_RESTORE_ON_RESET),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
