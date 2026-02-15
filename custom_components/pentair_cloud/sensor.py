"""Platform for sensor integration."""
from __future__ import annotations

import datetime
from dataclasses import dataclass
import time
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
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
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
        entities.append(PentairFlowTotalSensor(hub, device, daily=False))
        entities.append(PentairFlowTotalSensor(hub, device, daily=True))
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


class PentairFlowTotalSensor(RestoreEntity, SensorEntity):
    """Sensor that integrates flow rate over time to compute gallons."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.GALLONS
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:water"

    def __init__(
        self,
        hub: PentairCloudHub,
        pentair_device: PentairDevice,
        daily: bool,
    ) -> None:
        self.hub = hub
        self.pentair_device = pentair_device
        self._daily = daily
        self._total_gallons = 0.0
        self._last_update_ts: float | None = None
        self._last_reset_date: str | None = None

        if daily:
            self._attr_name = "Daily Gallons"
            self._attr_unique_id = (
                f"pentair_{pentair_device.pentair_device_id}_daily_gallons"
            )
            self._attr_state_class = SensorStateClass.TOTAL
        else:
            self._attr_name = "Total Gallons"
            self._attr_unique_id = (
                f"pentair_{pentair_device.pentair_device_id}_total_gallons"
            )
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING

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

    async def async_added_to_hass(self) -> None:
        """Restore state after restart."""
        await super().async_added_to_hass()
        last_data = await self.async_get_last_sensor_data()
        if last_data and last_data.native_value is not None:
            try:
                restored = float(last_data.native_value)
            except (ValueError, TypeError):
                restored = 0.0
            if self._daily:
                today = datetime.date.today().isoformat()
                if (
                    last_data.native_unit_of_measurement is not None
                    and hasattr(last_data, "native_value")
                ):
                    # Check extra stored state for last_reset date
                    last_state = await self.async_get_last_state()
                    last_reset_date = None
                    if last_state and last_state.attributes.get("last_reset"):
                        try:
                            last_reset_dt = datetime.datetime.fromisoformat(
                                last_state.attributes["last_reset"]
                            )
                            last_reset_date = last_reset_dt.date().isoformat()
                        except (ValueError, TypeError):
                            pass
                    if last_reset_date == today:
                        self._total_gallons = restored
                    else:
                        self._total_gallons = 0.0
                self._last_reset_date = datetime.date.today().isoformat()
                self._attr_last_reset = datetime.datetime.combine(
                    datetime.date.today(),
                    datetime.time.min,
                    tzinfo=datetime.timezone.utc,
                )
            else:
                self._total_gallons = restored
        # Always leave _last_update_ts = None so first interval is skipped
        self._last_update_ts = None

    @property
    def native_value(self) -> float | None:
        return round(self._total_gallons, 1)

    def update(self) -> None:
        """Integrate flow rate over elapsed time."""
        self.hub.update_pentair_devices_status()

        raw = self.pentair_device.sensor_data.get("s26")
        if raw is None:
            flow_gpm = 0.0
        else:
            try:
                flow_gpm = int(raw) / 10
            except (ValueError, TypeError):
                flow_gpm = 0.0

        now = time.monotonic()

        if self._last_update_ts is None:
            self._last_update_ts = now
            return

        elapsed = now - self._last_update_ts
        # Cap at 120 seconds to avoid counting long gaps (e.g. HA downtime)
        if elapsed > 120:
            elapsed = 120

        if self._daily:
            today = datetime.date.today().isoformat()
            if self._last_reset_date != today:
                self._total_gallons = 0.0
                self._last_reset_date = today
                self._attr_last_reset = datetime.datetime.combine(
                    datetime.date.today(),
                    datetime.time.min,
                    tzinfo=datetime.timezone.utc,
                )

        self._total_gallons += flow_gpm * (elapsed / 60)
        self._last_update_ts = now
