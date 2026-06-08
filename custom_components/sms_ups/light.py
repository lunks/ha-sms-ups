"""Light entity for SMS Legrand UPS RGB LED."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import SmsUpsConnectionError
from .coordinator import SmsUpsConfigEntry, SmsUpsCoordinator
from .entity import SmsUpsEntity

_LOGGER = logging.getLogger(__name__)

EFFECT_LIST = [
    "Solid",
    "Fade",
    "Rainbow",
    "Transition",
    "UPS Mode",
    "Battery Level",
    "Power Level",
]

# Maps effect name to API code
EFFECT_TO_CODE = {
    "Solid": 0,
    "Fade": 2,
    "Rainbow": 3,
    "Transition": 4,
    "UPS Mode": 5,
    "Battery Level": 6,
    "Power Level": 7,
}

# Maps API code to effect name
CODE_TO_EFFECT = {v: k for k, v in EFFECT_TO_CODE.items()}
CODE_TO_EFFECT[1] = "Solid"  # preset color is also solid


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmsUpsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMS UPS LED light."""
    coordinator = entry.runtime_data
    if coordinator.api.features.get("ledRGB") == "true":
        async_add_entities([SmsUpsLight(coordinator)])


class SmsUpsLight(SmsUpsEntity, LightEntity):
    """Representation of the SMS UPS RGB LED."""

    _attr_has_entity_name = True
    _attr_translation_key = "led"
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = EFFECT_LIST

    def __init__(self, coordinator: SmsUpsCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_id}_led_rgb"
        self._state: dict[str, Any] = {}

    @property
    def is_on(self) -> bool | None:
        """Return whether the LED is on."""
        if not self._state:
            return None
        return self._state.get("enabled") == 1

    @property
    def brightness(self) -> int | None:
        """Return brightness (0-255)."""
        if not self._state:
            return None
        # API uses 0-100 alpha, HA uses 0-255
        alpha = self._state.get("alpha", 100)
        return round(alpha * 255 / 100)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return RGB color."""
        if not self._state:
            return None
        return (
            self._state.get("red", 0),
            self._state.get("green", 0),
            self._state.get("blue", 0),
        )

    @property
    def effect(self) -> str | None:
        """Return current effect."""
        if not self._state:
            return None
        code = self._state.get("effect", 0)
        return CODE_TO_EFFECT.get(code, "Solid")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the LED on with optional color/brightness/effect."""
        try:
            # Enable first if off
            if not self.is_on:
                await self.coordinator.api.set_led_enabled(True)

            if ATTR_EFFECT in kwargs:
                effect_name = kwargs[ATTR_EFFECT]
                code = EFFECT_TO_CODE.get(effect_name, 0)
                await self.coordinator.api.set_led_color(effect=code)

            if ATTR_RGB_COLOR in kwargs or ATTR_BRIGHTNESS in kwargs:
                r, g, b = kwargs.get(ATTR_RGB_COLOR, self.rgb_color or (0, 0, 255))
                brightness = kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255)
                alpha = round(brightness * 100 / 255)
                await self.coordinator.api.set_led_color(
                    red=r, green=g, blue=b, alpha=alpha
                )

            await self._async_refresh_state()
        except SmsUpsConnectionError as err:
            raise HomeAssistantError(f"Failed to control LED: {err}") from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the LED off."""
        try:
            await self.coordinator.api.set_led_enabled(False)
            await self._async_refresh_state()
        except SmsUpsConnectionError as err:
            raise HomeAssistantError(f"Failed to turn off LED: {err}") from err

    async def async_added_to_hass(self) -> None:
        """Fetch initial LED state when added."""
        await super().async_added_to_hass()
        await self._async_refresh_state()

    async def _async_refresh_state(self) -> None:
        """Fetch LED state from the API."""
        try:
            self._state = await self.coordinator.api.get_led_state()
            self.async_write_ha_state()
        except SmsUpsConnectionError:
            _LOGGER.debug("Failed to refresh LED state")
