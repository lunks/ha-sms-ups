"""TLS context for the SMS Legrand UPS local API.

The UPS serves a factory-provisioned leaf certificate (its CN encodes the device
MAC, e.g. ``d:ups_wifi:<mac>``) issued by Legrand's private "Legrand Brazil Root
CA". We trust only that bundled root, so a man-in-the-middle on the LAN cannot
impersonate the device. Hostname checking is disabled because the certificate's
CN is the device MAC, not its IP address.
"""

from __future__ import annotations

import ssl
from functools import lru_cache
from pathlib import Path

_ROOT_CA = Path(__file__).parent / "legrand_root_ca.pem"


@lru_cache(maxsize=1)
def get_ssl_context() -> ssl.SSLContext:
    """Return an SSLContext that verifies the device against the Legrand root CA."""
    ctx = ssl.create_default_context(cafile=str(_ROOT_CA))
    ctx.check_hostname = False
    return ctx
