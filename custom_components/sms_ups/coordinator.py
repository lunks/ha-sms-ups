"""Data update coordinator for SMS Legrand UPS."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmsUpsApi, SmsUpsAuthError, SmsUpsConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type SmsUpsConfigEntry = ConfigEntry[SmsUpsCoordinator]

METER_KEY_MAP = {
    "Tensao de Entrada": "input_voltage",
    "Tensao de Saida": "output_voltage",
    "Nivel da Bateria": "battery_level",
    "Nivel de Bateria": "battery_level",
    "Potencia de Saida": "output_power",
    "Temperatura": "temperature",
    "Frequencia de Saida": "output_frequency",
    "Tipo": "ups_type",
}

STATE_KEY_MAP = {
    "Nobreak": "ups_active",
    "Carga da Bateria": "battery_charging",
    "Rede Eletrica": "grid_power",
    "Teste": "battery_test",
    "Boost": "boost",
    "ByPass": "bypass",
    "Potencia Elevada": "overpower",
}


class SmsUpsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage polling the UPS device."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SmsUpsApi,
        config_entry: SmsUpsConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and normalize UPS data."""
        try:
            raw = await self.api.get_meters()
        except SmsUpsAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except SmsUpsConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err

        data: dict[str, Any] = {}

        for meter in raw.get("medidores", []):
            key = METER_KEY_MAP.get(meter.get("nome"))
            if key is None:
                continue
            fases = meter.get("fases", {})
            try:
                valor = float(fases.get("valor", 0))
            except (ValueError, TypeError):
                valor = fases.get("valor")
            data[key] = {
                "value": valor,
                "unit": meter.get("unidade", ""),
                "max": fases.get("max"),
                "min": fases.get("min"),
            }

        for state in raw.get("estados", []):
            key = STATE_KEY_MAP.get(state.get("nome"))
            if key is not None:
                data[key] = state.get("valor", False)

        data["status"] = self._compute_status(data)

        return data

    @staticmethod
    def _compute_status(data: dict[str, Any]) -> str:
        """Derive UPS status string from state flags."""
        if data.get("ups_active"):
            battery = data.get("battery_level", {})
            level = battery.get("value") if isinstance(battery, dict) else None
            if level is not None and level < 20:
                return "Low Battery"
            return "On Battery"
        if data.get("battery_test"):
            return "Battery Test"
        if data.get("bypass"):
            return "Bypass"
        if data.get("boost"):
            return "Boost"
        if data.get("overpower"):
            return "Overpower"
        if data.get("grid_power"):
            return "Online"
        return "Unknown"
