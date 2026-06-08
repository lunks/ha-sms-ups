"""Base entity for SMS Legrand UPS."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmsUpsCoordinator


class SmsUpsEntity(CoordinatorEntity[SmsUpsCoordinator]):
    """Base entity for all SMS UPS entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmsUpsCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.api.serial)},
            name=coordinator.api.deploy_name,
            manufacturer="SMS Legrand",
            model=coordinator.api.model,
            serial_number=coordinator.api.serial,
        )
