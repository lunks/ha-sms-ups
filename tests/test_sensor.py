"""Tests for SMS Legrand UPS sensors."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_sensor_states(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """Numeric sensors expose the normalized meter values."""
    await _setup(hass, mock_config_entry)

    assert hass.states.get("sensor.office_ups_battery_level").state == "85.0"
    assert hass.states.get("sensor.office_ups_input_voltage").state == "220.5"
    assert hass.states.get("sensor.office_ups_output_voltage").state == "120.0"
    assert hass.states.get("sensor.office_ups_output_power").state == "42.0"


async def test_sensor_unique_ids(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """Unique IDs are serial-prefixed and never start with None_."""
    await _setup(hass, mock_config_entry)

    state = hass.states.get("sensor.office_ups_battery_level")
    assert state is not None

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get("sensor.office_ups_battery_level")
    assert entry.unique_id == "SN12345678_battery_level"
    assert not entry.unique_id.startswith("None_")
