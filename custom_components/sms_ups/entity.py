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
        api = coordinator.api
        # Fall back to the deploy id when the device omits a serial so that
        # unique ids and device identifiers never collapse to None.
        self._device_id = api.serial or api.deploy_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=api.deploy_name,
            manufacturer="SMS Legrand",
            model=api.model,
            serial_number=api.serial,
        )
