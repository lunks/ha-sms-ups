"""Button entities for SMS Legrand UPS."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import SmsUpsConnectionError
from .coordinator import SmsUpsConfigEntry, SmsUpsCoordinator
from .entity import SmsUpsEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class SmsUpsButtonDescription(ButtonEntityDescription):
    """Describe an SMS UPS button."""

    tipo_evento: str
    tempo: str = ""


BUTTON_DESCRIPTIONS: tuple[SmsUpsButtonDescription, ...] = (
    SmsUpsButtonDescription(
        key="test_battery_quick",
        translation_key="test_battery_quick",
        device_class=ButtonDeviceClass.RESTART,
        tipo_evento="1",
    ),
    SmsUpsButtonDescription(
        key="test_battery_deep",
        translation_key="test_battery_deep",
        device_class=ButtonDeviceClass.RESTART,
        tipo_evento="3",
    ),
    SmsUpsButtonDescription(
        key="test_battery_stop",
        translation_key="test_battery_stop",
        tipo_evento="4",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmsUpsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMS UPS buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmsUpsButton(coordinator, description) for description in BUTTON_DESCRIPTIONS
    )


class SmsUpsButton(SmsUpsEntity, ButtonEntity):
    """Representation of an SMS UPS button."""

    entity_description: SmsUpsButtonDescription

    def __init__(
        self,
        coordinator: SmsUpsCoordinator,
        description: SmsUpsButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._device_id}_{description.key}"

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.coordinator.api.send_command(
                self.entity_description.tipo_evento,
                self.entity_description.tempo,
            )
        except SmsUpsConnectionError as err:
            raise HomeAssistantError(f"Failed to send command: {err}") from err
