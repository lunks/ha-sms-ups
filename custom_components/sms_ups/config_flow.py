"""Config flow for SMS Legrand UPS."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmsUpsApi, SmsUpsAuthError, SmsUpsConnectionError
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SmsUpsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMS Legrand UPS."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_devices: list[dict[str, Any]] = []
        self._selected_device: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial step — auto-scan, then show results or fallback to manual."""
        self._discovered_devices = await SmsUpsApi.discover()

        if self._discovered_devices:
            return await self.async_step_select()

        return await self.async_step_not_found()

    async def async_step_not_found(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """No devices found — let user choose to retry or enter manually."""
        if user_input is not None:
            if user_input.get("action") == "manual":
                return await self.async_step_manual()
            return await self.async_step_user()

        return self.async_show_form(
            step_id="not_found",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="retry"): vol.In(
                        {"retry": "Scan again", "manual": "Enter manually"}
                    ),
                }
            ),
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show discovered devices."""
        if user_input is not None:
            choice = user_input["device"]
            if choice == "__manual__":
                return await self.async_step_manual()

            idx = int(choice)
            self._selected_device = self._discovered_devices[idx]
            return await self.async_step_credentials()

        options: dict[str, str] = {}
        for i, device in enumerate(self._discovered_devices):
            existing = any(
                entry.data.get(CONF_HOST) == device["host"]
                and entry.data.get(CONF_PORT) == device["port"]
                for entry in self._async_current_entries()
            )
            if existing:
                continue
            options[str(i)] = f"{device['name']} ({device['host']})"

        if not options:
            return self.async_abort(reason="all_configured")

        options["__manual__"] = "Enter manually..."

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({vol.Required("device"): vol.In(options)}),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual entry of host, port, username, password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error, api = await self._validate_connection(user_input)
            if error:
                errors["base"] = error
            else:
                return self._create_entry(user_input, api)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Enter credentials for a discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            full_input = {
                CONF_HOST: self._selected_device["host"],
                CONF_PORT: self._selected_device["port"],
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            error, api = await self._validate_connection(full_input)
            if error:
                errors["base"] = error
            else:
                return self._create_entry(full_input, api)

        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            description_placeholders={
                "name": self._selected_device["name"],
                "host": self._selected_device["host"],
            },
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when credentials become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth credential input."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            full_input = {
                **reauth_entry.data,
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            error, _ = await self._validate_connection(full_input)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(reauth_entry, data=full_input)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            description_placeholders={
                "host": reauth_entry.data[CONF_HOST],
            },
            errors=errors,
        )

    async def _validate_connection(
        self, user_input: dict[str, Any]
    ) -> tuple[str | None, SmsUpsApi | None]:
        """Validate the connection. Returns (error_key, api_on_success)."""
        session = async_get_clientsession(self.hass, verify_ssl=False)
        api = SmsUpsApi(
            host=user_input[CONF_HOST],
            port=user_input[CONF_PORT],
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
            session=session,
        )
        try:
            await api.login()
        except SmsUpsAuthError:
            return "invalid_auth", None
        except SmsUpsConnectionError:
            return "cannot_connect", None
        except Exception:
            _LOGGER.exception("Unexpected error during setup")
            return "unknown", None

        await self.async_set_unique_id(api.serial)
        self._abort_if_unique_id_configured()

        return None, api

    def _create_entry(
        self, user_input: dict[str, Any], api: SmsUpsApi | None = None
    ) -> ConfigFlowResult:
        """Create the config entry."""
        title = api.deploy_name if api else user_input[CONF_HOST]
        return self.async_create_entry(title=title, data=user_input)
