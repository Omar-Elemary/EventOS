from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import session_maker
from app.domain.models import VenueCandidate, Vendor
from app.models import ResearchRecord, Vendor as VendorRow, VendorService, Venue
from app.services.research import ResearchHit, utcnow
from app.tools.venue_search import location_matches


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class DbResearchMemory:
    async def get(self, key: str) -> ResearchHit | None:
        async with session_maker()() as session:
            row = await session.scalar(select(ResearchRecord).where(ResearchRecord.query_key == key))
            if not row:
                return None
            if _aware(row.expires_at) <= utcnow():
                return None
            return ResearchHit(
                kind=row.kind,
                query_key=row.query_key,
                query=row.query,
                payload=row.extracted_data if row.extracted_data else row.payload,
                source_type=row.source_type,
                fetched_at=_aware(row.fetched_at),
                expires_at=_aware(row.expires_at),
                fingerprint=row.fingerprint or "",
                provider=row.provider or "mock",
                source_url=row.source_url or "",
                source_tier=row.source_tier or "mock",
                confidence=float(row.confidence or 0.7),
                title=row.title or "",
                normalized_query=row.normalized_query or "",
            )

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
        async with session_maker()() as session:
            row = await session.scalar(select(ResearchRecord).where(ResearchRecord.query_key == key))
            if row:
                row.kind = kind
                row.query = query
                row.payload = payload
                row.extracted_data = payload
                row.source_type = source_type
                row.fingerprint = fingerprint
                row.fetched_at = now
                row.retrieved_at = now
                row.expires_at = now + timedelta(seconds=ttl_seconds)
                row.provider = provider
                row.source_url = source_url
                row.source_tier = source_tier
                row.confidence = confidence
                row.title = title
                row.normalized_query = normalized_query
                row.raw_reference = raw_reference
                if event_id:
                    row.event_id = event_id
            else:
                session.add(
                    ResearchRecord(
                        query_key=key,
                        event_id=event_id,
                        kind=kind,
                        query=query,
                        normalized_query=normalized_query,
                        source_url=source_url,
                        source_tier=source_tier,
                        title=title,
                        extracted_data=payload,
                        payload=payload,
                        source_type=source_type,
                        fingerprint=fingerprint,
                        fetched_at=now,
                        retrieved_at=now,
                        expires_at=now + timedelta(seconds=ttl_seconds),
                        confidence=confidence,
                        provider=provider,
                        raw_reference=raw_reference,
                    )
                )
            await session.commit()

    async def list_venues(self, location: str) -> list[dict[str, Any]]:
        async with session_maker()() as session:
            rows = (await session.execute(select(Venue))).scalars().all()
            out = []
            for row in rows:
                if not location_matches(location, row.location or ""):
                    continue
                extra = row.extra or {}
                out.append(
                    {
                        "name": row.name,
                        "location": row.location,
                        "capacity": row.capacity,
                        "estimated_cost": row.estimated_cost,
                        "facilities": row.facilities or [],
                        "suitability_score": extra.get("suitability_score", 50),
                        "pros": extra.get("pros") or [],
                        "cons": extra.get("cons") or [],
                        "source": extra.get("source") or "database catalog",
                        "source_type": row.source_type or "mock",
                        "selected": False,
                    }
                )
            return out

    async def upsert_venues(self, venues: list[VenueCandidate]) -> None:
        async with session_maker()() as session:
            for venue in venues:
                existing = await session.scalar(
                    select(Venue).where(Venue.name == venue.name, Venue.location == venue.location)
                )
                extra = {
                    "pros": venue.pros,
                    "cons": venue.cons,
                    "suitability_score": venue.suitability_score,
                    "source": venue.source,
                }
                source = venue.source_type.value if hasattr(venue.source_type, "value") else str(venue.source_type)
                if existing:
                    existing.capacity = venue.capacity
                    existing.estimated_cost = venue.estimated_cost
                    existing.facilities = venue.facilities
                    existing.source_type = source
                    existing.extra = extra
                else:
                    session.add(
                        Venue(
                            name=venue.name,
                            location=venue.location,
                            capacity=venue.capacity,
                            estimated_cost=venue.estimated_cost,
                            facilities=venue.facilities,
                            source_type=source,
                            extra=extra,
                        )
                    )
            await session.commit()

    async def list_vendors(self, location: str, category: str) -> list[dict[str, Any]]:
        async with session_maker()() as session:
            rows = (await session.execute(select(VendorRow).options(selectinload(VendorRow.services)))).scalars().all()
            out = []
            for row in rows:
                if row.category != category:
                    continue
                if not location_matches(location, row.location or ""):
                    continue
                services = []
                for s in row.services or []:
                    services.append({"name": s.name, "unit_cost": s.unit_cost, "notes": None})
                out.append(
                    {
                        "name": row.name,
                        "category": row.category,
                        "location": row.location,
                        "estimated_cost": row.estimated_cost,
                        "services": services,
                        "rating": row.rating,
                        "source_type": row.source_type or "mock",
                        "selected": True,
                    }
                )
            return out

    async def upsert_vendors(self, vendors: list[Vendor]) -> None:
        async with session_maker()() as session:
            for vendor in vendors:
                cat = vendor.category.value if hasattr(vendor.category, "value") else str(vendor.category)
                existing = await session.scalar(
                    select(VendorRow).where(VendorRow.name == vendor.name, VendorRow.category == cat)
                )
                source = vendor.source_type.value if hasattr(vendor.source_type, "value") else str(vendor.source_type)
                if existing:
                    existing.location = vendor.location
                    existing.estimated_cost = vendor.estimated_cost
                    existing.source_type = source
                    existing.rating = vendor.rating
                else:
                    row = VendorRow(
                        name=vendor.name,
                        category=cat,
                        location=vendor.location,
                        estimated_cost=vendor.estimated_cost,
                        source_type=source,
                        rating=vendor.rating,
                    )
                    session.add(row)
                    await session.flush()
                    for s in vendor.services:
                        session.add(VendorService(vendor_id=row.id, name=s.name, unit_cost=s.unit_cost))
            await session.commit()
