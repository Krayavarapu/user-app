from __future__ import annotations

import os

import httpx
import pytest


def test_api_keys_are_removed_from_environment() -> None:
    # app.main loads .env at import time; the autouse fixture must strip any real keys.
    assert os.getenv("OPENAI_API_KEY") is None
    assert os.getenv("ANTHROPIC_API_KEY") is None


def test_real_network_calls_are_blocked() -> None:
    with pytest.raises(AssertionError, match="network disabled in tests"):
        httpx.post("https://api.openai.com/v1/chat/completions", json={})


def test_mock_transport_still_works() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True})))
    assert client.post("https://api.anthropic.com/v1/messages", json={}).json() == {"ok": True}


def test_test_client_still_works(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}
