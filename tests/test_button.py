"""Tests for SMS Legrand UPS buttons."""

from __future__ import annotations

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import BASE_URL


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_button_press_sends_command(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """Pressing a button dispatches the right tipoEvento."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.office_ups_battery_test_quick"},
        blocking=True,
    )

    disparo_calls = [
        c for c in mock_api.mock_calls if "/sms/mobile/disparo" in str(c[1])
    ]
    assert disparo_calls
    # tipoEvento for the quick battery test is "1".
    assert "tipoEvento=1" in str(disparo_calls[-1][1])


async def test_button_press_api_error_raises(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    login_response: dict,
    meters_response: dict,
    led_response: dict,
) -> None:
    """An API error during a press surfaces as HomeAssistantError."""
    aioclient_mock.post(f"{BASE_URL}/sms/mobile/login/", json=login_response)
    aioclient_mock.get(f"{BASE_URL}/sms/mobile/medidores/", json=meters_response)
    aioclient_mock.get(f"{BASE_URL}/sms/mobile/ledRGB/", json=led_response)
    aioclient_mock.post(
        f"{BASE_URL}/sms/mobile/disparo", json={"responseStatus": "S999"}
    )
    await _setup(hass, mock_config_entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.office_ups_battery_test_quick"},
            blocking=True,
        )
