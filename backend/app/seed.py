from datetime import datetime, timezone
import os

from sqlalchemy import select

from app.core.db import init_engine, session_maker
from app.models import Event, User, Vendor, VendorService, Venue
from app.tools.mock_data import MOCK_VENUES, mock_vendors

DEMO_EVENT_ID = "11111111-1111-1111-1111-111111111111"
DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"


async def seed() -> None:
    init_engine()
    async with session_maker()() as session:
        from app.services.auth import hash_password

        existing = await session.get(User, DEMO_USER_ID)
        demo_hash = hash_password("demo1234")
        if not existing:
            session.add(
                User(
                    id=DEMO_USER_ID,
                    email="demo@eventos.local",
                    name="Jordan Diaz",
                    password_hash=demo_hash,
                )
            )
        elif not getattr(existing, "password_hash", None):
            existing.password_hash = demo_hash

        if os.getenv("VERCEL"):
            await session.commit()
            return

        vcount = (await session.execute(select(Venue))).scalars().first()
        if not vcount:
            for v in MOCK_VENUES:
                session.add(
                    Venue(
                        name=v.name,
                        location=v.location,
                        capacity=v.capacity,
                        estimated_cost=v.estimated_cost,
                        facilities=v.facilities,
                        source_type="mock",
                        extra={"pros": v.pros, "cons": v.cons, "suitability_score": v.suitability_score},
                    )
                )
            for vd in mock_vendors():
                row = Vendor(
                    name=vd.name,
                    category=vd.category.value,
                    location=vd.location,
                    estimated_cost=vd.estimated_cost,
                    source_type="mock",
                    rating=vd.rating,
                )
                session.add(row)
                await session.flush()
                for s in vd.services:
                    session.add(VendorService(vendor_id=row.id, name=s.name, unit_cost=s.unit_cost))

        ev = await session.get(Event, DEMO_EVENT_ID)
        if not ev:
            session.add(
                Event(
                    id=DEMO_EVENT_ID,
                    owner_id=DEMO_USER_ID,
                    name="AI Future Summit 2026",
                    location="Cairo",
                    start_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                    attendees=500,
                    duration_days=3,
                    budget=30000,
                    currency="USD",
                    status="draft",
                    user_request=(
                        "Plan a 3-day technology conference in Cairo for 500 attendees "
                        "with a $30,000 budget. Need conference hall, high-speed WiFi, AV, "
                        "catering, registration, photography, security, and transportation."
                    ),
                )
            )
        await session.commit()


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed())
