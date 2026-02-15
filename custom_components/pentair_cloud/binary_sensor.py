"""Platform for binary sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DEFAULT_POOL_SIZE, DEFAULT_TARGET_TURNOVERS
from .pentaircloud import PentairCloudHub, PentairDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up Pentair Cloud binary sensor entities."""
    hub: PentairCloudHub = hass.data[DOMAIN][config_entry.entry_id]["pentair_cloud_hub"]
    devices: list[PentairDevice] = await hass.async_add_executor_job(hub.get_devices)
    entities = []
    for device in devices:
        entities.append(PentairTurnoverTargetBinarySensor(hub, device, config_entry))
    async_add_entities(entities)


class PentairTurnoverTargetBinarySensor(BinarySensorEntity):
    """Binary sensor indicating whether the daily turnover target has been met."""

    _attr_has_entity_name = True
    _attr_name = "Pool Turnover Target Met"
    _attr_icon = "mdi:check-circle-outline"

    def __init__(
        self,
        hub: PentairCloudHub,
        pentair_device: PentairDevice,
        config_entry: ConfigEntry,
    ) -> None:
        self.hub = hub
        self.pentair_device = pentair_device
        self._config_entry = config_entry
        self._attr_unique_id = (
            f"pentair_{pentair_device.pentair_device_id}_turnover_target_met"
        )

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, f"pentair_{self.pentair_device.pentair_device_id}")
            },
            "name": self.pentair_device.nickname,
            "model": self.pentair_device.nickname,
            "sw_version": "1.0",
            "manufacturer": "Pentair",
        }

    def _get_values(self) -> tuple[float, int, float]:
        """Return (daily_gallons, pool_size, target_turnovers)."""
        device_id = self.pentair_device.pentair_device_id
        entry_data = self.hass.data.get(DOMAIN, {}).get(
            self._config_entry.entry_id, {}
        )
        daily_gallons = entry_data.get("daily_gallons", {}).get(device_id, 0.0)
        pool_size = self._config_entry.options.get(
            f"pool_size_{device_id}", DEFAULT_POOL_SIZE
        )
        target_turnovers = self._config_entry.options.get(
            f"target_turnovers_{device_id}", DEFAULT_TARGET_TURNOVERS
        )
        return daily_gallons, pool_size, target_turnovers

    @property
    def is_on(self) -> bool:
        daily_gallons, pool_size, target_turnovers = self._get_values()
        return daily_gallons >= pool_size * target_turnovers

    @property
    def extra_state_attributes(self) -> dict:
        daily_gallons, pool_size, target_turnovers = self._get_values()
        return {
            "pool_size_gallons": pool_size,
            "target_turnovers": target_turnovers,
            "target_gallons": round(pool_size * target_turnovers, 1),
            "daily_gallons": round(daily_gallons, 1),
        }

    def update(self) -> None:
        self.hub.update_pentair_devices_status()
