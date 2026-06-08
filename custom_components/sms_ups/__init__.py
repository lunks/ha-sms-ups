"""SMS Legrand UPS integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmsUpsApi, SmsUpsAuthError, SmsUpsConnectionError
from .const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from .coordinator import SmsUpsConfigEntry, SmsUpsCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: SmsUpsConfigEntry) -> bool:
    """Set up SMS Legrand UPS from a config entry."""
    session = async_get_clientsession(hass, verify_ssl=False)
    api = SmsUpsApi(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=session,
    )
    try:
        await api.login()
    except SmsUpsAuthError as err:
        raise ConfigEntryAuthFailed(
            f"Authentication failed for {entry.data[CONF_HOST]}"
        ) from err
    except SmsUpsConnectionError as err:
        raise ConfigEntryNotReady(f"Cannot connect to {entry.data[CONF_HOST]}") from err

    coordinator = SmsUpsCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmsUpsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
