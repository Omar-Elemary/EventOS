"""Research memory: search once, persist, reuse until TTL or inputs change."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Protocol

from app.domain.enums import VendorCategory
from app.domain.models import (
    ConversionResult,
    CurrencyConversionInput,
    EventRequirements,
    VenueCandidate,
    VenueSearchInput,
    Vendor,
    VendorSearchInput,
    WeatherLookupInput,
    WeatherResult,
    WebResearchInput,
    WebResearchResult,
)
from app.tools.venue_search import location_matches, score_venues

TTL = {
    "venue": 7 * 24 * 3600,
    "vendor": 7 * 24 * 3600,
    "weather": 6 * 3600,
    "fx": 12 * 3600,
    "web": 3 * 24 * 3600,
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def query_key(kind: str, **parts: Any) -> str:
    payload = {"kind": kind, **parts}
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class ResearchHit:
    kind: str
    query_key: str
    query: str
    payload: Any
    source_type: str
    fetched_at: datetime
    expires_at: datetime
    fingerprint: str = ""
    provider: str = "mock"
    source_url: str = ""
    source_tier: str = "mock"
    confidence: float = 0.7
    title: str = ""
    normalized_query: str = ""

    @property
    def fresh(self) -> bool:
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > utcnow()


class ResearchMemory(Protocol):
    async def get(self, key: str) -> ResearchHit | None: ...

    async def put(
        self,
        key: str,
        *,
        kind: str,
        query: str,
        payload: Any,
        source_type: str,
        ttl_seconds: int,
        fingerprint: str = "",
        event_id: str | None = None,
        provider: str = "mock",
        source_url: str = "",
        source_tier: str = "mock",
        confidence: float = 0.7,
        title: str = "",
        normalized_query: str = "",
        raw_reference: str = "",
    ) -> None: ...

    async def list_venues(self, location: str) -> list[dict[str, Any]]: ...

    async def upsert_venues(self, venues: list[VenueCandidate]) -> None: ...

    async def list_vendors(self, location: str, category: str) -> list[dict[str, Any]]: ...

    async def upsert_vendors(self, vendors: list[Vendor]) -> None: ...


@dataclass
class InMemoryResearchMemory:
    hits: dict[str, ResearchHit] = field(default_factory=dict)
    venues: list[dict[str, Any]] = field(default_factory=list)
    vendors: list[dict[str, Any]] = field(default_factory=list)

    async def get(self, key: str) -> ResearchHit | None:
        hit = self.hits.get(key)
        if hit and hit.fresh:
            return hit
        return None

    async def put(
        self,
        key: str,
        *,
        kind: str,
        query: str,
        payload: Any,
        source_type: str,
        ttl_seconds: int,
        fingerprint: str = "",
        event_id: str | None = None,
        provider: str = "mock",
        source_url: str = "",
        source_tier: str = "mock",
        confidence: float = 0.7,
        title: str = "",
        normalized_query: str = "",
        raw_reference: str = "",
    ) -> None:
        now = utcnow()
        self.hits[key] = ResearchHit(
            kind=kind,
            query_key=key,
            query=query,
            payload=payload,
            source_type=source_type,
            fetched_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            fingerprint=fingerprint,
            provider=provider,
            source_url=source_url,
            source_tier=source_tier,
            confidence=confidence,
            title=title,
            normalized_query=normalized_query,
        )

    async def list_venues(self, location: str) -> list[dict[str, Any]]:
        return [v for v in self.venues if location_matches(location, str(v.get("location") or ""))]

    async def upsert_venues(self, venues: list[VenueCandidate]) -> None:
        by_name = {(v.get("name"), v.get("location")): i for i, v in enumerate(self.venues)}
        for venue in venues:
            data = venue.model_dump(mode="json")
            pair = (data.get("name"), data.get("location"))
            if pair in by_name:
                self.venues[by_name[pair]] = data
            else:
                by_name[pair] = len(self.venues)
                self.venues.append(data)

    async def list_vendors(self, location: str, category: str) -> list[dict[str, Any]]:
        return [
            v
            for v in self.vendors
            if str(v.get("category")) == category and location_matches(location, str(v.get("location") or ""))
        ]

    async def upsert_vendors(self, vendors: list[Vendor]) -> None:
        by_name = {(v.get("name"), v.get("category")): i for i, v in enumerate(self.vendors)}
        for vendor in vendors:
            data = vendor.model_dump(mode="json")
            pair = (data.get("name"), data.get("category"))
            if pair in by_name:
                self.vendors[by_name[pair]] = data
            else:
                by_name[pair] = len(self.vendors)
                self.vendors.append(data)


def _dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [_dump(x) for x in obj]
    return obj


def _mark_cached(items: list[Any], model) -> list[Any]:
    out = []
    for item in items:
        obj = item if isinstance(item, model) else model.model_validate(item)
        out.append(obj.model_copy(update={"from_cache": True}))
    return out


async def _cached(
    memory: ResearchMemory,
    *,
    kind: str,
    key: str,
    query: str,
    fingerprint: str,
    event_id: str | None,
    force: bool,
    fetch: Callable[[], Awaitable[tuple[Any, str]]],
) -> tuple[Any, bool, str]:
    if not force:
        hit = await memory.get(key)
        if hit:
            return hit.payload, True, hit.source_type
    payload, source = await fetch()
    await memory.put(
        key,
        kind=kind,
        query=query,
        payload=_dump(payload),
        source_type=source,
        ttl_seconds=TTL[kind],
        fingerprint=fingerprint,
        event_id=event_id,
    )
    return payload, False, source


def _req_facilities(req: EventRequirements) -> list[str]:
    fac = list(req.requirements or [])
    if req.format == "outdoor" and "outdoor" not in [f.lower() for f in fac]:
        fac.append("outdoor space")
    return fac


async def research_venues(
    deps,
    req: EventRequirements,
    *,
    event_id: str | None = None,
    force: bool = False,
) -> tuple[list[VenueCandidate], bool]:
    payload_in = VenueSearchInput(
        location=req.location or "",
        attendee_count=req.attendees,
        event_type=req.event_type,
        required_facilities=_req_facilities(req),
        format=req.format,
    )
    fp = query_key(
        "venue",
        location=payload_in.location.lower(),
        attendees=payload_in.attendee_count,
        event_type=payload_in.event_type,
        facilities=sorted(f.lower() for f in payload_in.required_facilities),
        fmt=payload_in.format or "",
    )

    async def fetch() -> tuple[list[VenueCandidate], str]:
        if getattr(deps.tools, "use_mock", True):
            catalog = await deps.research.list_venues(payload_in.location)
            if catalog:
                scored = score_venues([VenueCandidate.model_validate(v) for v in catalog], payload_in)
                if scored:
                    st = scored[0].source_type
                    source = st.value if hasattr(st, "value") else str(st)
                    return scored, source
        results = await deps.tools.venue_search.execute(payload_in)
        if results:
            await deps.research.upsert_venues(results)
        source = "mock"
        if results:
            st = results[0].source_type
            source = st.value if hasattr(st, "value") else str(st)
        return results, source

    raw, cached, _source = await _cached(
        deps.research,
        kind="venue",
        key=fp,
        query=f"venues {payload_in.location} {payload_in.event_type} n={payload_in.attendee_count}",
        fingerprint=fp,
        event_id=event_id,
        force=force,
        fetch=fetch,
    )
    venues = [v if isinstance(v, VenueCandidate) else VenueCandidate.model_validate(v) for v in raw]
    venues = [v for v in venues if location_matches(payload_in.location, v.location)]
    if cached:
        venues = _mark_cached(venues, VenueCandidate)
    return venues, cached


async def research_vendors(
    deps,
    req: EventRequirements,
    category: VendorCategory,
    *,
    event_id: str | None = None,
    force: bool = False,
) -> tuple[list[Vendor], bool]:
    inp = VendorSearchInput(
        category=category,
        location=req.location or "",
        budget=req.budget,
        required_services=[],
    )
    fp = query_key("vendor", location=(req.location or "").lower(), category=category.value, budget=req.budget)

    async def fetch() -> tuple[list[Vendor], str]:
        if getattr(deps.tools, "use_mock", True):
            catalog = await deps.research.list_vendors(inp.location, category.value)
            if catalog:
                found = [Vendor.model_validate(v) for v in catalog][:3]
                source = "mock"
                if found:
                    st = found[0].source_type
                    source = st.value if hasattr(st, "value") else str(st)
                return found, source
        found = await deps.tools.vendor_search.execute(inp)
        if found:
            await deps.research.upsert_vendors(found)
        source = "mock"
        if found:
            st = found[0].source_type
            source = st.value if hasattr(st, "value") else str(st)
        return found, source

    raw, cached, _source = await _cached(
        deps.research,
        kind="vendor",
        key=fp,
        query=f"{category.value} vendors in {inp.location}",
        fingerprint=fp,
        event_id=event_id,
        force=force,
        fetch=fetch,
    )
    vendors = [v if isinstance(v, Vendor) else Vendor.model_validate(v) for v in raw]
    vendors = [v for v in vendors if location_matches(inp.location, v.location)]
    if cached:
        vendors = _mark_cached(vendors, Vendor)
    return vendors, cached


async def research_weather(
    deps,
    location: str,
    date: str,
    *,
    event_id: str | None = None,
    force: bool = False,
) -> tuple[WeatherResult, bool]:
    fp = query_key("weather", location=location.lower(), date=date)

    async def fetch() -> tuple[WeatherResult, str]:
        result = await deps.tools.weather_lookup.execute(WeatherLookupInput(location=location, date=date))
        st = result.source_type
        return result, st.value if hasattr(st, "value") else str(st)

    raw, cached, _source = await _cached(
        deps.research,
        kind="weather",
        key=fp,
        query=f"weather {location} {date}",
        fingerprint=fp,
        event_id=event_id,
        force=force,
        fetch=fetch,
    )
    weather = raw if isinstance(raw, WeatherResult) else WeatherResult.model_validate(raw)
    if cached:
        weather = weather.model_copy(update={"from_cache": True})
    return weather, cached


async def research_fx(
    deps,
    amount: float,
    from_currency: str,
    to_currency: str,
    *,
    event_id: str | None = None,
    force: bool = False,
) -> ConversionResult:
    fp = query_key("fx", amount=amount, src=from_currency.upper(), dst=to_currency.upper())

    async def fetch() -> tuple[ConversionResult, str]:
        result = await deps.tools.currency_conversion.execute(
            CurrencyConversionInput(amount=amount, from_currency=from_currency, to_currency=to_currency)
        )
        st = result.source_type
        return result, st.value if hasattr(st, "value") else str(st)

    raw, cached, _source = await _cached(
        deps.research,
        kind="fx",
        key=fp,
        query=f"{amount} {from_currency}->{to_currency}",
        fingerprint=fp,
        event_id=event_id,
        force=force,
        fetch=fetch,
    )
    conv = raw if isinstance(raw, ConversionResult) else ConversionResult.model_validate(raw)
    if cached:
        conv = conv.model_copy(update={"from_cache": True})
    return conv


async def research_web(
    deps,
    query: str,
    *,
    kind: str = "web",
    location: str | None = None,
    event_id: str | None = None,
    force: bool = False,
) -> tuple[WebResearchResult, bool]:
    fp = query_key("web", q=query.lower(), topic=kind, location=(location or "").lower())

    async def fetch() -> tuple[WebResearchResult, str]:
        result = await deps.tools.web_research.execute(
            WebResearchInput(query=query, kind=kind, location=location)
        )
        st = result.source_type
        return result, st.value if hasattr(st, "value") else str(st)

    raw, cached, _source = await _cached(
        deps.research,
        kind="web",
        key=fp,
        query=query,
        fingerprint=fp,
        event_id=event_id,
        force=force,
        fetch=fetch,
    )
    result = raw if isinstance(raw, WebResearchResult) else WebResearchResult.model_validate(raw)
    if cached:
        result = result.model_copy(update={"from_cache": True})
    return result, cached


async def prefetch_evidence(deps, req: EventRequirements, event_id: str | None = None) -> None:
    """RUN-time research prefetch. Graph then operates over cached evidence."""
    import asyncio

    from app.services.intake import weather_date

    loc = req.location or ""
    date = weather_date(req)
    cats = [
        VendorCategory.catering,
        VendorCategory.av,
        VendorCategory.security,
        VendorCategory.photography,
        VendorCategory.staffing,
        VendorCategory.transportation,
    ]
    if req.accommodation or req.overnight:
        cats.append(VendorCategory.hotels)
    if req.stage:
        cats.append(VendorCategory.stage)
    tasks = [
        research_venues(deps, req, event_id=event_id),
        research_weather(deps, loc, date, event_id=event_id),
        research_web(deps, f"event permits regulations {loc} Egypt", kind="regulations", location=loc, event_id=event_id),
    ]
    for cat in cats:
        tasks.append(research_vendors(deps, req, cat, event_id=event_id))
    await asyncio.gather(*tasks, return_exceptions=True)
