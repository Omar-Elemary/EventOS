from app.domain.enums import DataSourceType, VendorCategory
from app.domain.models import Vendor, VendorSearchInput, VendorService
from app.tools.base import Tool
from app.tools.mock_data import mock_vendors
from app.tools.normalization.location import normalize_location

OSM_QUERY = {
    VendorCategory.catering: "catering restaurant {loc}",
    VendorCategory.photography: "photographer {loc}",
    VendorCategory.videography: "video production {loc}",
    VendorCategory.security: "security services {loc}",
    VendorCategory.transportation: "coach bus hire {loc}",
    VendorCategory.decoration: "event decoration {loc}",
    VendorCategory.av: "audio visual production {loc}",
    VendorCategory.lighting: "event lighting {loc}",
    VendorCategory.entertainment: "live music entertainment {loc}",
    VendorCategory.staffing: "event staffing {loc}",
    VendorCategory.hotels: "hotel {loc}",
    VendorCategory.printing: "print shop {loc}",
    VendorCategory.tents: "tent rental {loc}",
    VendorCategory.generator: "generator rental {loc}",
    VendorCategory.medical: "ambulance {loc}",
    VendorCategory.stage: "stage rental {loc}",
}


class MockVendorSearchTool(Tool[VendorSearchInput, list[Vendor]]):
    name = "vendor_search"
    description = "Search mock vendor catalog. Results are simulated."
    input_model = VendorSearchInput

    async def _run(self, payload: VendorSearchInput) -> list[Vendor]:
        loc = payload.location.lower().replace("alexendria", "alexandria")
        egypt = any(x in loc for x in ("cairo", "giza", "alexandria", "sahel", "egypt", "hurghada", "sharm"))
        needed = {s.lower() for s in payload.required_services}
        matches = []
        for v in mock_vendors():
            if v.category != payload.category:
                continue
            if loc and loc not in v.location.lower() and not egypt:
                city = normalize_location(payload.location).city or payload.location
                v = v.model_copy(update={"location": city})
            elif egypt and loc:
                city = normalize_location(payload.location).city or payload.location
                v = v.model_copy(update={"location": city})
            if needed:
                names = {s.name.lower() for s in v.services}
                if not (needed & names) and payload.required_services:
                    pass
            if payload.budget and v.estimated_cost > payload.budget * 0.6:
                v = v.model_copy(update={"coverage_notes": "Costly vs remaining budget"})
            matches.append(v)
        matches.sort(key=lambda x: x.estimated_cost)
        return matches[:3]


class RealVendorSearchTool(Tool[VendorSearchInput, list[Vendor]]):
    name = "vendor_search"
    description = "Search OpenStreetMap for local vendors in a category."
    input_model = VendorSearchInput

    async def _run(self, payload: VendorSearchInput) -> list[Vendor]:
        from app.tools.live_apis import nominatim_search

        q = OSM_QUERY.get(payload.category, "vendor {loc}").format(loc=payload.location)
        rows = await nominatim_search(q, limit=5)
        vendors: list[Vendor] = []
        for i, row in enumerate(rows):
            name = str(row.get("name") or "").strip() or str(row.get("display_name") or "Vendor").split(",")[0]
            display = str(row.get("display_name") or payload.location)
            cost = 800 + i * 250
            vendors.append(
                Vendor(
                    name=name,
                    category=payload.category,
                    location=display,
                    estimated_cost=float(cost),
                    services=[VendorService(name=payload.category.value, unit_cost=float(cost), notes="OSM listing")],
                    rating=4.0,
                    coverage_notes="Live OSM listing; cost is an estimate",
                    source_type=DataSourceType.live,
                    selected=True,
                    source_url="",
                    source_tier="web",
                    price_type="estimated",
                    requires_quote=True,
                    provider="nominatim",
                )
            )
        vendors.sort(key=lambda x: x.estimated_cost)
        return vendors[:3]
