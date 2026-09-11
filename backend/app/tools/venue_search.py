from app.domain.enums import DataSourceType
from app.domain.models import VenueCandidate, VenueSearchInput
from app.tools.base import Tool
from app.tools.mock_data import MOCK_VENUES
from app.tools.normalization.location import bilingual_queries, normalize_location
from app.tools.normalization.sources import confidence_for_tier, source_tier_from_url


def location_matches(loc: str, venue_location: str) -> bool:
    loc_city = normalize_location(loc).city.lower()
    vcity = normalize_location(venue_location).city.lower()
    loc = loc.lower().replace("alexendria", "alexandria")
    vloc = venue_location.lower()
    if not loc:
        return True
    if loc_city and vcity and (loc_city in vcity or vcity in loc_city):
        return True
    if loc in vloc or vloc in loc:
        return True
    if "alexandria" in loc or loc_city == "alexandria":
        return "alexandria" in vloc or vcity == "alexandria"
    if loc_city in {"cairo", "giza", "new cairo", "nasr city", "heliopolis"}:
        return vcity in {"cairo", "giza", "new cairo", "nasr city", "heliopolis"} or any(
            x in vloc for x in ("cairo", "giza")
        )
    return False


def local_stub_venue(payload: VenueSearchInput) -> VenueCandidate:
    city = normalize_location(payload.location).city or (payload.location or "Local").strip() or "Local"
    cap = max(int(payload.attendee_count or 0) + 150, 250)
    return VenueCandidate(
        name=f"{city} Civic Hall",
        location=city,
        capacity=cap,
        estimated_cost=float(max(900, cap * 5)),
        facilities=["WiFi", "AV equipment", "registration area", "catering kitchen"],
        suitability_score=68,
        pros=["Local to the brief", "Sized for the headcount"],
        cons=["Generic mock listing — confirm availability"],
        source="EventOS mock local fallback",
        source_type=DataSourceType.mock,
        selected=True,
    )


def score_venues(candidates: list[VenueCandidate], payload: VenueSearchInput) -> list[VenueCandidate]:
    loc = payload.location.lower().replace("alexendria", "alexandria")
    needed = {f.lower() for f in payload.required_facilities}
    results: list[VenueCandidate] = []
    for v in candidates:
        if loc and not location_matches(loc, v.location):
            continue
        cap_score = 100 if v.capacity >= payload.attendee_count else max(0, 100 * v.capacity / payload.attendee_count)
        fac_score = 100
        if needed:
            have = {f.lower() for f in v.facilities}
            fac_score = 100 * len(needed & have) / len(needed)
        type_bonus = 100
        et = payload.event_type.lower()
        fac_blob = " ".join(v.facilities).lower()
        if "music" in et or "classic" in et or "concert" in et:
            type_bonus = 100 if "acoustic" in fac_blob or "opera" in v.name.lower() else 70
        elif "conference" in et:
            type_bonus = 100
        if payload.format == "outdoor" and "outdoor" not in fac_blob and "garden" not in fac_blob:
            type_bonus = min(type_bonus, 60)
        score = round(0.5 * cap_score + 0.3 * fac_score + 0.2 * type_bonus, 1)
        results.append(v.model_copy(update={"suitability_score": min(100, score), "selected": False}))
    if not results:
        return []
    results.sort(key=lambda x: (-(x.capacity >= payload.attendee_count), -x.suitability_score, x.estimated_cost))
    if results:
        for r in results:
            if r.capacity >= payload.attendee_count:
                r.selected = True
                break
        else:
            results[0].selected = True
    return results


class MockVenueSearchTool(Tool[VenueSearchInput, list[VenueCandidate]]):
    name = "venue_search"
    description = "Search mock venue catalog. Results are simulated, not live listings."
    input_model = VenueSearchInput

    async def _run(self, payload: VenueSearchInput) -> list[VenueCandidate]:
        results = score_venues(MOCK_VENUES, payload)
        if not results:
            return [local_stub_venue(payload)]
        return results


class RealVenueSearchTool(Tool[VenueSearchInput, list[VenueCandidate]]):
    name = "venue_search"
    description = "Discover venue sources (Brave) then enrich with Nominatim. App owns normalized rows."
    input_model = VenueSearchInput

    async def _run(self, payload: VenueSearchInput) -> list[VenueCandidate]:
        from datetime import datetime, timezone

        from app.domain.enums import PriceType, ResearchProvider, SourceTier
        from app.tools.live_apis import brave_search, nominatim_search

        loc = normalize_location(payload.location)
        et = payload.event_type.lower()
        kind = "conference venue"
        if "music" in et or "concert" in et or "classic" in et:
            kind = "concert hall"
        elif "wedding" in et:
            kind = "event venue"
        now = datetime.now(timezone.utc)
        discovered: list[dict] = []
        try:
            for q in bilingual_queries(kind, loc.city or payload.location, extra=str(payload.attendee_count)):
                discovered.extend(await brave_search(q, count=5))
        except Exception:
            discovered = []
        rows = await nominatim_search(f"{kind} {loc.label}", limit=8)
        if not rows:
            rows = await nominatim_search(f"venue {loc.city}", limit=8)
        candidates: list[VenueCandidate] = []
        for i, row in enumerate(rows):
            name = str(row.get("name") or "").strip() or str(row.get("display_name") or "Venue").split(",")[0]
            display = str(row.get("display_name") or loc.label)
            hit = next((h for h in discovered if name.lower()[:12] in (h.get("title") or "").lower()), discovered[i] if i < len(discovered) else None)
            url = (hit or {}).get("url") or ""
            tier = source_tier_from_url(url) if url else SourceTier.web
            osm_type = str(row.get("type") or "")
            capacity = 800 if "conference" in osm_type else 400
            if "theatre" in osm_type or "opera" in osm_type:
                capacity = 600
            if "stadium" in osm_type:
                capacity = 5000
            if "hotel" in osm_type:
                capacity = 450
            cost = 4000 + i * 800 + (capacity // 10)
            facilities = ["WiFi"]
            if payload.format == "outdoor":
                facilities.append("outdoor space")
            if "conference" in et:
                facilities.extend(["AV equipment", "registration area"])
            candidates.append(
                VenueCandidate(
                    name=name,
                    location=display,
                    capacity=capacity,
                    estimated_cost=float(cost),
                    facilities=facilities,
                    suitability_score=50,
                    pros=[f"Discovered via {'Brave + ' if url else ''}Nominatim"],
                    cons=["Capacity and cost are estimates — vendor quote required"],
                    source=url or "OpenStreetMap Nominatim",
                    source_type=DataSourceType.live,
                    source_url=url,
                    source_tier=tier,
                    confidence=confidence_for_tier(tier),
                    retrieved_at=now,
                    last_checked_at=now,
                    price_type=PriceType.estimated,
                    requires_quote=True,
                    provider=ResearchProvider.brave if url else ResearchProvider.nominatim,
                )
            )
        for i, hit in enumerate(discovered):
            title = (hit.get("title") or "").split(" - ")[0].strip()
            if not title or any(c.name.lower() == title.lower() for c in candidates):
                continue
            url = hit.get("url") or ""
            tier = source_tier_from_url(url)
            candidates.append(
                VenueCandidate(
                    name=title[:255],
                    location=loc.label,
                    capacity=max(payload.attendee_count, 100),
                    estimated_cost=5000 + i * 500,
                    facilities=["WiFi"],
                    suitability_score=40,
                    pros=["Found online — verify"],
                    cons=["Listing is a web discovery, not a verified booking"],
                    source=url,
                    source_type=DataSourceType.live,
                    source_url=url,
                    source_tier=tier,
                    confidence=confidence_for_tier(tier),
                    retrieved_at=now,
                    last_checked_at=now,
                    price_type=PriceType.estimated,
                    requires_quote=True,
                    provider=ResearchProvider.brave,
                )
            )
        return score_venues(candidates, payload) if candidates else []
