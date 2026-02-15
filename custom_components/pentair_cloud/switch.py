"""Platform for switch integration."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, DEBUG_INFO
from .pentaircloud import PentairCloudHub, PentairDevice, PentairPumpProgram
from logging import Logger

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    hub = hass.data[DOMAIN][config_entry.entry_id]["pentair_cloud_hub"]
    devices: list[PentairDevice] = await hass.async_add_executor_job(hub.get_devices)
    cloud_devices = []
    for device in devices:
        for program in device.programs:
            cloud_devices.append(PentairCloudSwitch(_LOGGER, hub, device, program))
    async_add_entities(cloud_devices)


class PentairCloudSwitch(SwitchEntity):
    global DOMAIN
    global DEBUG_INFO

    _attr_has_entity_name = True

    def __init__(
        self,
        LOGGER: Logger,
        hub: PentairCloudHub,
        pentair_device: PentairDevice,
        pentair_program: PentairPumpProgram,
    ) -> None:
        self.LOGGER = LOGGER
        self.hub = hub
        self.pentair_device = pentair_device
        self.pentair_program = pentair_program
        self._attr_name = self.pentair_program.name
        self._state = self.pentair_program.running
        self._scheduled_refreshes: list[CALLBACK_TYPE] = []
        if DEBUG_INFO:
            self.LOGGER.info("Pentair Cloud Pump " + self._attr_name + " Configured")

    @property
    def unique_id(self):
        return (
            f"pentair_"
            + self.pentair_device.pentair_device_id
            + "_"
            + str(self.pentair_program.id)
        )

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, f"pentair_" + self.pentair_device.pentair_device_id)
            },
            "name": self.pentair_device.nickname,
            "model": self.pentair_device.nickname,
            "sw_version": "1.0",
            "manufacturer": "Pentair",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        if DEBUG_INFO:
            self.LOGGER.info(
                "Pentair Cloud Pump "
                + self.pentair_device.pentair_device_id
                + " Called IS_ON"
            )
        self._state = self.pentair_program.running
        return self._state

    async def async_turn_on(self, **kwargs) -> None:
        """Instruct the switch to turn on."""
        if DEBUG_INFO:
            self.LOGGER.info(
                "Pentair Cloud Pump "
                + self.pentair_device.pentair_device_id
                + " Called ON program: "
                + str(self.pentair_program.id)
            )
        self._state = True
        await self.hass.async_add_executor_job(
            self.hub.start_program,
            self.pentair_device.pentair_device_id,
            self.pentair_program.id,
        )
        self.hub.notify_action()
        self._schedule_refreshes()

    async def async_turn_off(self, **kwargs) -> None:
        """Instruct the switch to turn off."""
        if DEBUG_INFO:
            self.LOGGER.info(
                "Pentair Cloud Pump "
                + self.pentair_device.pentair_device_id
                + " Called OFF program: "
                + str(self.pentair_program.id)
            )
        self._state = False
        await self.hass.async_add_executor_job(
            self.hub.stop_program,
            self.pentair_device.pentair_device_id,
            self.pentair_program.id,
        )
        self.hub.notify_action()
        self._schedule_refreshes()

    def _schedule_refreshes(self) -> None:
        """Schedule tapering refresh callbacks after an action."""
        # Cancel any previously scheduled refreshes
        for cancel in self._scheduled_refreshes:
            cancel()
        self._scheduled_refreshes.clear()

        async def _refresh(_now) -> None:
            await self.async_update_ha_state(force_refresh=True)

        delays = []
        # Every 5s from 5–60s (12 callbacks)
        delays.extend(range(5, 61, 5))
        # Every 15s from 75–180s (8 callbacks)
        delays.extend(range(75, 181, 15))
        # Every 30s from 210–300s (4 callbacks)
        delays.extend(range(210, 301, 30))

        for delay in delays:
            cancel = async_call_later(self.hass, delay, _refresh)
            self._scheduled_refreshes.append(cancel)

    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending scheduled refreshes on entity removal."""
        for cancel in self._scheduled_refreshes:
            cancel()
        self._scheduled_refreshes.clear()

    def update(self) -> None:
        """Fetch new state data for this switch."""
        self.hub.update_pentair_devices_status()
        self._state = self.pentair_program.running
        if DEBUG_INFO:
            self.LOGGER.info(
                "Pentair Cloud Pump "
                + self.pentair_device.pentair_device_id
                + " Called UPDATE"
            )
