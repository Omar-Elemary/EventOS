"""Live HTTP lookups used when USE_MOCK_TOOLS is false.

Weather: Open-Meteo (no key). FX: Frankfurter (no key).
Places: Nominatim/OpenStreetMap (no key, 1 req/s).
Web: Brave Search if SEARCH_API_KEY is set.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core.config import get_settings
from app.core.http import get_http_client

USER_AGENT = "EventOS/1.0 (event planning research cache)"
_NOMINATIM_LOCK = asyncio.Lock()
_last_nominatim = 0.0


async def _get_json(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    merged = {"User-Agent": USER_AGENT, **(headers or {})}
    client = get_http_client()
    resp = await client.get(url, params=params, headers=merged, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


async def nominatim_search(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    global _last_nominatim
    async with _NOMINATIM_LOCK:
        wait = 1.05 - (time.monotonic() - _last_nominatim)
        if wait > 0:
            await asyncio.sleep(wait)
        data = await _get_json(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": str(limit)},
        )
        _last_nominatim = time.monotonic()
    return data if isinstance(data, list) else []


async def geocode(location: str) -> tuple[float, float] | None:
    data = await _get_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1},
    )
    results = (data or {}).get("results") or []
    if not results:
        return None
    return float(results[0]["latitude"]), float(results[0]["longitude"])


async def open_meteo_weather(location: str, date: str) -> dict[str, Any]:
    coords = await geocode(location)
    if not coords:
        raise RuntimeError(f"Could not geocode {location}")
    lat, lon = coords
    data = await _get_json(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,precipitation_probability_max,weathercode",
            "start_date": date,
            "end_date": date,
            "timezone": "auto",
        },
    )
    daily = data.get("daily") or {}
    temps = daily.get("temperature_2m_max") or [20]
    precip = daily.get("precipitation_probability_max") or [10]
    codes = daily.get("weathercode") or [0]
    temp = float(temps[0] if temps else 20)
    chance = float(precip[0] if precip else 10) / 100.0
    code = int(codes[0] if codes else 0)
    condition = _weather_label(code)
    return {"temp_c": temp, "precipitation_chance": min(1.0, max(0.0, chance)), "condition": condition}


def _weather_label(code: int) -> str:
    if code == 0:
        return "clear"
    if code in {1, 2, 3}:
        return "partly cloudy"
    if code in {45, 48}:
        return "fog"
    if code in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return "rain"
    if code in {71, 73, 75, 85, 86}:
        return "snow"
    if code in {95, 96, 99}:
        return "thunderstorms"
    return "mixed"


async def frankfurter_rate(from_currency: str, to_currency: str) -> float:
    src = from_currency.upper()
    dst = to_currency.upper()
    if src == dst:
        return 1.0
    data = await _get_json(
        "https://api.frankfurter.app/latest",
        params={"from": src, "to": dst},
    )
    rates = data.get("rates") or {}
    if dst not in rates:
        raise RuntimeError(f"No live FX rate for {src}->{dst}")
    return float(rates[dst])


async def brave_search(query: str, *, count: int = 5) -> list[dict[str, str]]:
    settings = get_settings()
    key = (settings.search_api_key or "").strip()
    if not key:
        raise RuntimeError("SEARCH_API_KEY is not configured")
    url = settings.search_api_url or "https://api.search.brave.com/res/v1/web/search"
    data = await _get_json(
        url,
        params={"q": query, "count": str(count)},
        headers={"X-Subscription-Token": key, "Accept": "application/json"},
    )
    results = ((data or {}).get("web") or {}).get("results") or []
    hits = []
    for row in results[:count]:
        hits.append(
            {
                "title": str(row.get("title") or ""),
                "url": str(row.get("url") or ""),
                "snippet": str(row.get("description") or row.get("snippet") or ""),
            }
        )
    return hits
