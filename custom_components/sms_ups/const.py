"""Constants for the SMS Legrand UPS integration."""

from enum import StrEnum

DOMAIN = "sms_ups"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DEFAULT_PORT = 443
DEFAULT_SCAN_INTERVAL = 30

DISCOVERY_PORT = 10250
DISCOVERY_MSG = "_powerview-remote._tcp.local."
DISCOVERY_TIMEOUT = 5

# Battery level (%) below which the UPS is reported as "low battery".
LOW_BATTERY_THRESHOLD = 20


class ResponseStatus(StrEnum):
    """`responseStatus` codes returned by the UPS HTTP API."""

    OK = "S001"
    TOKEN_EXPIRED = "S010"
    SESSION_INVALID = "S003"


# `tipoEvento` command values that accept a `tempo` (duration) argument.
EVENTS_WITH_DURATION = frozenset({"2", "8"})
