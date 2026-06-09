"""Tests for the bundled Legrand-root SSL context."""

from __future__ import annotations

import ssl

from custom_components.sms_ups.ssl_context import get_ssl_context


def test_ssl_context_pins_legrand_root() -> None:
    """The context verifies the chain but trusts only the bundled Legrand root."""
    ctx = get_ssl_context()
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.check_hostname is False
    assert ctx.verify_mode is ssl.CERT_REQUIRED

    cas = ctx.get_ca_certs()
    assert len(cas) == 1  # only Legrand's root, no system CAs
    subject = {k: v for rdn in cas[0]["subject"] for k, v in rdn}
    assert subject["organizationName"] == "Legrand"
    assert subject["commonName"] == "Legrand Brazil Root CA"
