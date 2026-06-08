"""Tests for the SMS Legrand UPS data coordinator and API session handling."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from .conftest import BASE_URL


def _sequence(payloads: list[dict[str, Any]]):
    """Return an async side_effect yielding payloads, repeating the last."""
    queue = list(payloads)

    async def _side_effect(method, url, data):
        payload = queue.pop(0) if len(queue) > 1 else queue[0]
        return AiohttpClientMockResponse(method, url, json=payload)

    return _side_effect


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> Any:
    """Set up the entry and return its coordinator."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data


async def test_meters_parse_and_normalize(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """Meters are normalized through METER_KEY_MAP / STATE_KEY_MAP."""
    coordinator = await _setup(hass, mock_config_entry)
    data = coordinator.data

    # Meters (numeric, normalized keys + units)
    assert data["input_voltage"]["value"] == 220.5
    assert data["input_voltage"]["unit"] == "V"
    assert data["battery_level"]["value"] == 85.0
    assert data["output_power"]["value"] == 42.0

    # States (booleans, normalized keys)
    assert data["grid_power"] is True
    assert data["battery_charging"] is True
    assert data["ups_active"] is False

    # Model extracted from the "Tipo" meter
    assert coordinator.api.model == "Senoidal 1500VA"


async def test_token_expiry_triggers_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    login_response: dict[str, Any],
    meters_response: dict[str, Any],
) -> None:
    """An S010 meters response triggers a token refresh then a retry."""
    aioclient_mock.post(f"{BASE_URL}/sms/mobile/login/", json=login_response)
    aioclient_mock.post(f"{BASE_URL}/sms/mobile/login/atualiza", json=login_response)
    # First meters call returns S010, subsequent calls succeed.
    aioclient_mock.get(
        f"{BASE_URL}/sms/mobile/medidores/",
        side_effect=_sequence([{"responseStatus": "S010"}, meters_response]),
    )

    coordinator = await _setup(hass, mock_config_entry)

    # Refresh endpoint was hit at least once.
    refresh_calls = [
        c
        for c in aioclient_mock.mock_calls
        if "/sms/mobile/login/atualiza" in str(c[1])
    ]
    assert len(refresh_calls) >= 1
    assert coordinator.data["grid_power"] is True


async def test_session_invalid_triggers_relogin(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    login_response: dict[str, Any],
    meters_response: dict[str, Any],
) -> None:
    """An S003 meters response triggers a re-login then a retry."""
    aioclient_mock.post(
        f"{BASE_URL}/sms/mobile/login/",
        side_effect=_sequence([login_response]),
    )
    aioclient_mock.get(
        f"{BASE_URL}/sms/mobile/medidores/",
        side_effect=_sequence([{"responseStatus": "S003"}, meters_response]),
    )

    coordinator = await _setup(hass, mock_config_entry)

    # login endpoint was hit at least twice (setup + re-login on S003).
    login_calls = [
        c
        for c in aioclient_mock.mock_calls
        if "/sms/mobile/login/" in str(c[1]) and "atualiza" not in str(c[1])
    ]
    assert len(login_calls) >= 2
    assert coordinator.data["grid_power"] is True
