"""Config flow for PentairCloud integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, DEFAULT_POOL_SIZE, DEFAULT_TARGET_TURNOVERS

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    from .pentaircloud import PentairCloudHub

    hub = PentairCloudHub(_LOGGER)
    if not await hass.async_add_executor_job(
        hub.authenticate, data["username"], data["password"]
    ):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": "Pentair Cloud"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PentairCloud."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Pentair Cloud options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._devices: list = []
        self._device_index: int = 0
        self._options: dict[str, Any] = dict(config_entry.options)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start the options flow."""
        hub = self.hass.data[DOMAIN][self.config_entry.entry_id]["pentair_cloud_hub"]
        self._devices = await self.hass.async_add_executor_job(hub.get_devices)
        if not self._devices:
            return self.async_abort(reason="no_devices")
        self._device_index = 0
        return await self.async_step_device()

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a single device."""
        device = self._devices[self._device_index]
        device_id = device.pentair_device_id

        if user_input is not None:
            self._options[f"pool_size_{device_id}"] = user_input["pool_size"]
            self._options[f"target_turnovers_{device_id}"] = user_input[
                "target_turnovers"
            ]
            self._device_index += 1
            if self._device_index < len(self._devices):
                return await self.async_step_device()
            return self.async_create_entry(title="", data=self._options)

        current_pool_size = self._options.get(
            f"pool_size_{device_id}", DEFAULT_POOL_SIZE
        )
        current_target = self._options.get(
            f"target_turnovers_{device_id}", DEFAULT_TARGET_TURNOVERS
        )

        schema = vol.Schema(
            {
                vol.Required("pool_size", default=current_pool_size): vol.All(
                    vol.Coerce(int), vol.Range(min=100, max=1000000)
                ),
                vol.Required("target_turnovers", default=current_target): vol.All(
                    vol.Coerce(float), vol.Range(min=0.1, max=10.0)
                ),
            }
        )

        return self.async_show_form(
            step_id="device",
            data_schema=schema,
            description_placeholders={"device_name": device.nickname},
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
