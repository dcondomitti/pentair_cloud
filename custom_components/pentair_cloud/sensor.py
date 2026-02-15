"""Platform for sensor integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .pentaircloud import PentairCloudHub, PentairDevice

_LOGGER = logging.getLogger(__name__)


def _tenths_to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return round(int(value) / 10, 1)
    except (ValueError, TypeError):
        return None


def _hundredths_to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return round(int(value) / 100, 2)
    except (ValueError, TypeError):
        return None


def _int_value(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _seconds_to_hours(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return round(int(value) / 3600, 1)
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True, kw_only=True)
class PentairSensorEntityDescription(SensorEntityDescription):
    """Describes a Pentair Cloud sensor."""

    field_key: str
    value_fn: Callable[[str | None], float | int | None]


SENSOR_DESCRIPTIONS: tuple[PentairSensorEntityDescription, ...] = (
    PentairSensorEntityDescription(
        key="internal_temperature",
        translation_key="internal_temperature",
        name="Internal Temperature",
        field_key="s41",
        value_fn=_tenths_to_float,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="current_motor_speed",
        translation_key="current_motor_speed",
        name="Current Motor Speed",
        field_key="s19",
        value_fn=_tenths_to_float,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        icon="mdi:pump",
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="current_estimated_flow",
        translation_key="current_estimated_flow",
        name="Current Estimated Flow",
        field_key="s26",
        value_fn=_tenths_to_float,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="GPM",
        suggested_display_precision=1,
        icon="mdi:water-pump",
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="current_power",
        translation_key="current_power",
        name="Current Power",
        field_key="s18",
        value_fn=_int_value,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="current_pressure",
        translation_key="current_pressure",
        name="Current Pressure",
        field_key="s17",
        value_fn=_hundredths_to_float,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.PSI,
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="drive_inverter_temperature",
        translation_key="drive_inverter_temperature",
        name="Drive Inverter Temperature",
        field_key="s38",
        value_fn=_tenths_to_float,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    PentairSensorEntityDescription(
        key="drive_pfc_temperature",
        translation_key="drive_pfc_temperature",
        name="Drive PFC Temperature",
        field_key="s39",
        value_fn=_tenths_to_float,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    PentairSensorEntityDescription(
        key="drive_supply_voltage",
        translation_key="drive_supply_voltage",
        name="Drive Supply Voltage",
        field_key="s40",
        value_fn=_hundredths_to_float,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    PentairSensorEntityDescription(
        key="motor_run_time",
        translation_key="motor_run_time",
        name="Motor Run Time",
        field_key="s36",
        value_fn=_seconds_to_hours,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        icon="mdi:timer-outline",
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="wifi_signal_level",
        translation_key="wifi_signal_level",
        name="WiFi Signal Level",
        field_key="s48",
        value_fn=_int_value,
        icon="mdi:wifi",
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="remaining_time",
        translation_key="remaining_time",
        name="Remaining Time",
        field_key="s28",
        value_fn=_int_value,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-sand",
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="relay_1_status",
        translation_key="relay_1_status",
        name="Relay 1 Status",
        field_key="s21",
        value_fn=_int_value,
        icon="mdi:electric-switch",
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="relay_2_status",
        translation_key="relay_2_status",
        name="Relay 2 Status",
        field_key="s22",
        value_fn=_int_value,
        icon="mdi:electric-switch",
        entity_registry_enabled_default=True,
    ),
    PentairSensorEntityDescription(
        key="alarm_condition",
        translation_key="alarm_condition",
        name="Alarm Condition",
        field_key="s20",
        value_fn=_int_value,
        icon="mdi:alarm-light-outline",
        entity_registry_enabled_default=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up Pentair Cloud sensor entities."""
    hub: PentairCloudHub = hass.data[DOMAIN][config_entry.entry_id]["pentair_cloud_hub"]
    devices: list[PentairDevice] = await hass.async_add_executor_job(hub.get_devices)
    entities = []
    for device in devices:
        for description in SENSOR_DESCRIPTIONS:
            entities.append(PentairCloudSensor(hub, device, description))
    async_add_entities(entities)


class PentairCloudSensor(SensorEntity):
    """Representation of a Pentair Cloud sensor."""

    entity_description: PentairSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        hub: PentairCloudHub,
        pentair_device: PentairDevice,
        description: PentairSensorEntityDescription,
    ) -> None:
        self.hub = hub
        self.pentair_device = pentair_device
        self.entity_description = description
        self._attr_unique_id = (
            f"pentair_{self.pentair_device.pentair_device_id}_{description.key}"
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

    @property
    def native_value(self) -> float | int | None:
        raw = self.pentair_device.sensor_data.get(self.entity_description.field_key)
        return self.entity_description.value_fn(raw)

    def update(self) -> None:
        """Fetch new state data for this sensor."""
        self.hub.update_pentair_devices_status()
