"""Tests for the SMS Legrand UPS config flow."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.sms_ups.const import DOMAIN

from .conftest import HOST, PORT

DISCOVERED = [{"name": "Office UPS", "host": HOST, "port": PORT}]
CREDS = {CONF_USERNAME: "admin", CONF_PASSWORD: "secret"}


@pytest.fixture
def mock_discover_found() -> Generator[Any]:
    """Patch discovery to return a single device."""
    with patch(
        "custom_components.sms_ups.config_flow.SmsUpsApi.discover",
        return_value=DISCOVERED,
    ) as mock:
        yield mock


@pytest.fixture
def mock_discover_none() -> Generator[Any]:
    """Patch discovery to return nothing."""
    with patch(
        "custom_components.sms_ups.config_flow.SmsUpsApi.discover",
        return_value=[],
    ) as mock:
        yield mock


async def _start(hass: HomeAssistant) -> dict[str, Any]:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )


async def test_discovery_select_credentials_creates_entry(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_discover_found: Any,
) -> None:
    """Discovery -> select -> credentials -> entry."""
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device": "0"}
    )
    assert result["step_id"] == "credentials"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], CREDS)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == HOST
    assert result["result"].unique_id == "SN12345678"


async def test_manual_path(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_discover_found: Any,
) -> None:
    """Choosing manual from the select step creates an entry."""
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device": "__manual__"}
    )
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: HOST, CONF_PORT: PORT, **CREDS},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "SN12345678"


async def test_not_found_to_manual(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    mock_discover_none: Any,
) -> None:
    """No devices found -> not_found form -> manual entry."""
    result = await _start(hass)
    assert result["step_id"] == "not_found"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"action": "manual"}
    )
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: HOST, CONF_PORT: PORT, **CREDS},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_all_configured_abort(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
    mock_discover_found: Any,
) -> None:
    """If the only discovered device is configured, the select step aborts."""
    mock_config_entry.add_to_hass(hass)
    result = await _start(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "all_configured"


async def test_invalid_auth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_discover_found: Any,
) -> None:
    """Bad credentials surface invalid_auth on the credentials step."""
    aioclient_mock.post(
        f"https://{HOST}:{PORT}/sms/mobile/login/",
        json={"responseStatus": "S005"},
    )
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device": "0"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CREDS)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_cannot_connect(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_discover_found: Any,
) -> None:
    """A connection error surfaces cannot_connect on the credentials step."""
    aioclient_mock.post(
        f"https://{HOST}:{PORT}/sms/mobile/login/",
        exc=TimeoutError(),
    )
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device": "0"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CREDS)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_unique_id_abort(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    login_response: dict[str, Any],
    mock_discover_none: Any,
) -> None:
    """A second entry whose login returns an existing serial aborts."""
    mock_config_entry.add_to_hass(hass)
    # A different address that authenticates as the same serial.
    aioclient_mock.post("https://10.0.0.9:443/sms/mobile/login/", json=login_response)

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"action": "manual"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.9", CONF_PORT: PORT, **CREDS},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
