"""Binary sensor entities for SMS Legrand UPS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SmsUpsConfigEntry, SmsUpsCoordinator
from .entity import SmsUpsEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SmsUpsBinarySensorDescription(BinarySensorEntityDescription):
    """Describe an SMS UPS binary sensor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[SmsUpsBinarySensorDescription, ...] = (
    SmsUpsBinarySensorDescription(
        key="grid_power",
        translation_key="grid_power",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda d: d.get("grid_power"),
    ),
    SmsUpsBinarySensorDescription(
        key="battery_charging",
        translation_key="battery_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda d: d.get("battery_charging"),
    ),
    SmsUpsBinarySensorDescription(
        key="ups_active",
        translation_key="ups_active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.get("ups_active"),
    ),
    SmsUpsBinarySensorDescription(
        key="boost",
        translation_key="boost",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.get("boost"),
    ),
    SmsUpsBinarySensorDescription(
        key="bypass",
        translation_key="bypass",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.get("bypass"),
    ),
    SmsUpsBinarySensorDescription(
        key="overpower",
        translation_key="overpower",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.get("overpower"),
    ),
    SmsUpsBinarySensorDescription(
        key="battery_test",
        translation_key="battery_test",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.get("battery_test"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmsUpsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMS UPS binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmsUpsBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class SmsUpsBinarySensor(SmsUpsEntity, BinarySensorEntity):
    """Representation of an SMS UPS binary sensor."""

    entity_description: SmsUpsBinarySensorDescription

    def __init__(
        self,
        coordinator: SmsUpsCoordinator,
        description: SmsUpsBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
