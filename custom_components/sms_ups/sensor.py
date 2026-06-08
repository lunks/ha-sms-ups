"""Sensor entities for SMS Legrand UPS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SmsUpsConfigEntry, SmsUpsCoordinator
from .entity import SmsUpsEntity


@dataclass(frozen=True, kw_only=True)
class SmsUpsSensorDescription(SensorEntityDescription):
    """Describe an SMS UPS sensor."""

    value_fn: Callable[[dict[str, Any]], float | str | None]


SENSOR_DESCRIPTIONS: tuple[SmsUpsSensorDescription, ...] = (
    SmsUpsSensorDescription(
        key="status",
        translation_key="status",
        icon="mdi:information-outline",
        value_fn=lambda d: d.get("status"),
    ),
    SmsUpsSensorDescription(
        key="battery_level",
        translation_key="battery_level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("battery_level", {}).get("value"),
    ),
    SmsUpsSensorDescription(
        key="output_power",
        translation_key="output_power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:gauge",
        value_fn=lambda d: d.get("output_power", {}).get("value"),
    ),
    SmsUpsSensorDescription(
        key="input_voltage",
        translation_key="input_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda d: d.get("input_voltage", {}).get("value"),
    ),
    SmsUpsSensorDescription(
        key="output_voltage",
        translation_key="output_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda d: d.get("output_voltage", {}).get("value"),
    ),
    SmsUpsSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("temperature", {}).get("value"),
    ),
    SmsUpsSensorDescription(
        key="output_frequency",
        translation_key="output_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("output_frequency", {}).get("value"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmsUpsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMS UPS sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmsUpsSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class SmsUpsSensor(SmsUpsEntity, SensorEntity):
    """Representation of an SMS UPS sensor."""

    entity_description: SmsUpsSensorDescription

    def __init__(
        self,
        coordinator: SmsUpsCoordinator,
        description: SmsUpsSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._device_id}_{description.key}"

    @property
    def native_value(self) -> float | str | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
