"""Tests for the SMS Legrand UPS RGB LED light."""

from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.components.light import (
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

ENTITY_ID = "light.office_ups_led"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _led_param_calls(mock: AiohttpClientMocker) -> list[str]:
    return [str(c[1]) for c in mock.mock_calls if "/sms/mobile/ledRGB/" in str(c[1])]


async def test_light_reflects_state(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """The light reflects the LED state returned by the device."""
    await _setup(hass, mock_config_entry)

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "on"
    # Fixture: blue at full alpha, effect 0 -> Solid.
    assert state.attributes[ATTR_RGB_COLOR] == (0, 0, 255)
    assert state.attributes[ATTR_BRIGHTNESS] == 255
    assert state.attributes[ATTR_EFFECT] == "Solid"


async def test_light_turn_on_color_and_brightness(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """Turning on with rgb + brightness maps alpha 0-255 -> 0-100."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_RGB_COLOR: (255, 128, 0),
            ATTR_BRIGHTNESS: 255,
        },
        blocking=True,
    )

    calls = _led_param_calls(mock_api)
    color_calls = [c for c in calls if "red=255" in c]
    assert color_calls
    last = color_calls[-1]
    assert "green=128" in last
    assert "blue=0" in last
    # brightness 255 -> alpha 100
    assert "alpha=100" in last


async def test_light_turn_on_effect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """Turning on with an effect maps the effect name to its API code."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_EFFECT: "Rainbow"},
        blocking=True,
    )

    calls = _led_param_calls(mock_api)
    # Rainbow -> effect code 3.
    assert any("effect=3" in c for c in calls)


async def test_light_turn_off(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """Turning off disables the LED via en=0."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )

    calls = _led_param_calls(mock_api)
    assert any("en=0" in c for c in calls)
