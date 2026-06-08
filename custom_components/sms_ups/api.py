"""API client for SMS Legrand UPS Wi-Fi devices."""

from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any

import aiohttp

from .const import (
    DISCOVERY_MSG,
    DISCOVERY_PORT,
    DISCOVERY_TIMEOUT,
    EVENTS_WITH_DURATION,
    ResponseStatus,
)

_LOGGER = logging.getLogger(__name__)


class SmsUpsAuthError(Exception):
    """Authentication error."""


class SmsUpsConnectionError(Exception):
    """Connection error."""


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    """UDP protocol for UPS device discovery."""

    def __init__(self) -> None:
        self.devices: list[dict[str, Any]] = []
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            text = data.decode("utf-8").strip()
            for line in text.splitlines():
                parts = line.split("\t")
                if len(parts) >= 3:
                    self.devices.append(
                        {"name": parts[0], "host": parts[1], "port": int(parts[2])}
                    )
        except (ValueError, UnicodeDecodeError):
            _LOGGER.debug("Failed to parse discovery response from %s", addr)


class SmsUpsApi:
    """API client for SMS Legrand UPS."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._session = session
        self._base_url = f"https://{host}:{port}"
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

        self.token: str | None = None
        self.refresh_token_value: str | None = None
        self.deploy_id: str | None = None
        self.deploy_name: str | None = None
        self.serial: str | None = None
        self.model: str | None = None
        self.features: dict[str, str] = {}

    async def login(self) -> dict[str, Any]:
        """Authenticate with the UPS device."""
        url = f"{self._base_url}/sms/mobile/login/"
        params = {
            "username": self._username,
            "password": self._password,
            "iddevice": "ha-sms-ups",
            "sodevice": "linux",
        }
        try:
            async with self._session.post(
                url, params=params, ssl=self._ssl_context
            ) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SmsUpsConnectionError(f"Cannot connect to {self._host}") from err

        status = data.get("responseStatus")
        if status != ResponseStatus.OK:
            raise SmsUpsAuthError(f"Login failed: {status}")

        self.token = data["token"]
        self.refresh_token_value = data["refreshToken"]
        self.deploy_id = data["deployId"]
        self.deploy_name = data.get("deployName", self._host)
        self.serial = data.get("serie")
        self.features = data.get("features", {})

        return data

    async def _refresh_token(self) -> None:
        """Refresh the authentication token."""
        url = f"{self._base_url}/sms/mobile/login/atualiza"
        params = {"refreshToken": self.refresh_token_value}
        try:
            async with self._session.post(
                url, params=params, ssl=self._ssl_context
            ) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SmsUpsConnectionError("Token refresh failed") from err

        if data.get("responseStatus") == ResponseStatus.OK:
            self.token = data["token"]
            self.refresh_token_value = data["refreshToken"]
        else:
            await self.login()

    async def get_meters(self) -> dict[str, Any]:
        """Fetch real-time UPS metrics."""
        url = f"{self._base_url}/sms/mobile/medidores/"
        headers = {"token": self.token, "deployid": self.deploy_id}

        try:
            async with self._session.get(
                url, headers=headers, ssl=self._ssl_context
            ) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SmsUpsConnectionError(f"Cannot fetch meters: {err}") from err

        status = data.get("responseStatus")

        if status == ResponseStatus.TOKEN_EXPIRED:
            _LOGGER.debug("Token expired, refreshing")
            await self._refresh_token()
            return await self._get_meters_raw()

        if status == ResponseStatus.SESSION_INVALID:
            _LOGGER.debug("Session invalid, re-authenticating")
            await self.login()
            return await self._get_meters_raw()

        if status != ResponseStatus.OK:
            raise SmsUpsConnectionError(f"Unexpected response: {status}")

        # Extract model from meters (first time only)
        if self.model is None:
            for meter in data.get("medidores", []):
                if meter.get("nome") == "Tipo":
                    self.model = meter.get("fases", {}).get("valor")
                    break

        return data

    async def _get_meters_raw(self) -> dict[str, Any]:
        """Fetch meters without retry logic (used after token refresh)."""
        url = f"{self._base_url}/sms/mobile/medidores/"
        headers = {"token": self.token, "deployid": self.deploy_id}

        async with self._session.get(
            url, headers=headers, ssl=self._ssl_context
        ) as resp:
            data = await resp.json(content_type=None)

        if data.get("responseStatus") != ResponseStatus.OK:
            raise SmsUpsConnectionError(
                f"Failed after re-auth: {data.get('responseStatus')}"
            )

        return data

    async def send_command(self, tipo_evento: str, tempo: str = "") -> None:
        """Send a command to the UPS."""
        url = f"{self._base_url}/sms/mobile/disparo"
        headers = {"token": self.token, "deployid": self.deploy_id}
        params: dict[str, str] = {"tipoEvento": tipo_evento}
        if tipo_evento in EVENTS_WITH_DURATION and tempo:
            params["tempo"] = tempo

        try:
            async with self._session.post(
                url, headers=headers, params=params, ssl=self._ssl_context
            ) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SmsUpsConnectionError(f"Command failed: {err}") from err

        status = data.get("responseStatus")
        if status == ResponseStatus.TOKEN_EXPIRED:
            await self._refresh_token()
            headers["token"] = self.token
            async with self._session.post(
                url, headers=headers, params=params, ssl=self._ssl_context
            ) as resp:
                data = await resp.json(content_type=None)

        if data.get("responseStatus") != ResponseStatus.OK:
            raise SmsUpsConnectionError(f"Command failed: {data.get('responseStatus')}")

    def _auth_headers(self) -> dict[str, str]:
        """Return auth headers for API requests."""
        return {"token": self.token, "deployid": self.deploy_id}

    async def _authed_request(
        self, method: str, path: str, params: dict | None = None
    ) -> dict[str, Any]:
        """Make an authenticated request with token refresh on expiry."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._auth_headers(),
                params=params,
                ssl=self._ssl_context,
            ) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SmsUpsConnectionError(f"Request failed: {err}") from err

        status = data.get("responseStatus")
        if status in (ResponseStatus.TOKEN_EXPIRED, ResponseStatus.SESSION_INVALID):
            if status == ResponseStatus.TOKEN_EXPIRED:
                await self._refresh_token()
            else:
                await self.login()
            async with self._session.request(
                method,
                url,
                headers=self._auth_headers(),
                params=params,
                ssl=self._ssl_context,
            ) as resp:
                data = await resp.json(content_type=None)

        return data

    async def get_led_state(self) -> dict[str, Any]:
        """Fetch LED RGB state."""
        data = await self._authed_request("GET", "/sms/mobile/ledRGB/")
        if data.get("responseStatus") != ResponseStatus.OK:
            raise SmsUpsConnectionError(
                f"LED state failed: {data.get('responseStatus')}"
            )
        return data

    async def set_led_enabled(self, enabled: bool) -> None:
        """Enable or disable the LED."""
        data = await self._authed_request(
            "POST",
            "/sms/mobile/ledRGB/",
            params={"en": "1" if enabled else "0"},
        )
        if data.get("responseStatus") != ResponseStatus.OK:
            raise SmsUpsConnectionError(
                f"LED enable failed: {data.get('responseStatus')}"
            )

    async def set_led_color(
        self,
        *,
        red: int | None = None,
        green: int | None = None,
        blue: int | None = None,
        alpha: int | None = None,
        effect: int | None = None,
        speed: int | None = None,
    ) -> None:
        """Set LED color, effect, or speed."""
        params: dict[str, str] = {}
        if effect is not None:
            params["effect"] = str(effect)
        if red is not None:
            params["red"] = str(red)
        if green is not None:
            params["green"] = str(green)
        if blue is not None:
            params["blue"] = str(blue)
        if alpha is not None:
            params["alpha"] = str(alpha)
        if speed is not None:
            params["speed"] = str(speed)
        if "red" in params:
            params.setdefault("defaultColor", "0")

        data = await self._authed_request(
            "POST",
            "/sms/mobile/ledRGB/",
            params=params,
        )
        if data.get("responseStatus") != ResponseStatus.OK:
            raise SmsUpsConnectionError(
                f"LED color failed: {data.get('responseStatus')}"
            )

    @staticmethod
    async def discover(
        duration: float = DISCOVERY_TIMEOUT,
    ) -> list[dict[str, Any]]:
        """Discover UPS devices on the local network via UDP broadcast."""
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            _DiscoveryProtocol,
            local_addr=("0.0.0.0", 0),
            allow_broadcast=True,
        )

        try:
            transport.sendto(
                DISCOVERY_MSG.encode("utf-8"),
                ("255.255.255.255", DISCOVERY_PORT),
            )
            await asyncio.sleep(duration)
        finally:
            transport.close()

        return protocol.devices
