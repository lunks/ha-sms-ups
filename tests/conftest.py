"""Common fixtures for the SMS Legrand UPS tests."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.sms_ups.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    DOMAIN,
)

HOST = "192.168.1.50"
PORT = 443
SERIAL = "SN12345678"
BASE_URL = f"https://{HOST}:{PORT}"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: Any,
) -> Generator[None]:
    """Enable loading of the custom integration in every test."""
    yield


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_json_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture from the tests/fixtures directory."""
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def login_response() -> dict[str, Any]:
    """Return a successful login payload."""
    return load_json_fixture("login.json")


@pytest.fixture
def meters_response() -> dict[str, Any]:
    """Return a meters payload."""
    return load_json_fixture("meters.json")


@pytest.fixture
def led_response() -> dict[str, Any]:
    """Return an LED state payload."""
    return load_json_fixture("led.json")


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry for the UPS."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Office UPS",
        unique_id=SERIAL,
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
        },
    )


@pytest.fixture
def mock_api(
    aioclient_mock: AiohttpClientMocker,
    login_response: dict[str, Any],
    meters_response: dict[str, Any],
    led_response: dict[str, Any],
) -> AiohttpClientMocker:
    """Register the device HTTP endpoints with aioclient_mock."""
    aioclient_mock.post(f"{BASE_URL}/sms/mobile/login/", json=login_response)
    aioclient_mock.post(f"{BASE_URL}/sms/mobile/login/atualiza", json=login_response)
    aioclient_mock.get(f"{BASE_URL}/sms/mobile/medidores/", json=meters_response)
    aioclient_mock.get(f"{BASE_URL}/sms/mobile/ledRGB/", json=led_response)
    aioclient_mock.post(
        f"{BASE_URL}/sms/mobile/ledRGB/", json={"responseStatus": "S001"}
    )
    aioclient_mock.post(
        f"{BASE_URL}/sms/mobile/disparo", json={"responseStatus": "S001"}
    )
    return aioclient_mock
