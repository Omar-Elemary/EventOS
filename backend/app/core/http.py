from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None
USER_AGENT = "EventOS/1.0 (event planning)"


def get_http_client(*, timeout: float = 25.0) -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=8.0),
            headers={"User-Agent": USER_AGENT},
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
