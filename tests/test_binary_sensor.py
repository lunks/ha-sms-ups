"""Tests for SMS Legrand UPS binary sensors."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_binary_sensor_states(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """Binary sensors reflect the normalized state flags."""
    await _setup(hass, mock_config_entry)

    assert hass.states.get("binary_sensor.office_ups_grid_power").state == "on"
    assert hass.states.get("binary_sensor.office_ups_battery_charging").state == "on"
    # "ups_active" is False in the fixture -> on-battery problem sensor is off.
    assert hass.states.get("binary_sensor.office_ups_on_battery").state == "off"
    assert hass.states.get("binary_sensor.office_ups_boost").state == "off"
    assert hass.states.get("binary_sensor.office_ups_bypass").state == "off"
