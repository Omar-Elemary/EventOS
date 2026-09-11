from app.domain.enums import DataSourceType
from app.domain.models import WebResearchHit, WebResearchInput, WebResearchResult
from app.tools.base import Tool

MOCK_NOTES = {
    "cairo": "Cairo peak traffic is 16:00-19:00 on the Nile Corniche; coaches should use a porte-cochere and a second loop at close. November is usually dry and mild.",
    "giza": "Giza access from downtown can add 45+ minutes; plan load-in the evening before and a shuttle from a central hotel cluster.",
    "alexandria": "Alexandria waterfront venues are wind-exposed; keep registration indoor and allow extra time for Corniche traffic.",
    "hurghada": "Hurghada transfers run from HRG; allow 20-40 minutes to resort venues and confirm coach access on the coastal road.",
    "sharm": "Sharm El-Sheikh venues are spread along the bay; budget extra transfer time and evening taxi surge after galas.",
    "sahel": "El Sahel / North Coast events are seasonal; confirm generator backup and water-tanker logistics if the site is off-grid.",
}


class MockWebResearchTool(Tool[WebResearchInput, WebResearchResult]):
    name = "web_research"
    description = "Local planning notes from a mock knowledge base (not live web)."
    input_model = WebResearchInput

    async def _run(self, payload: WebResearchInput) -> WebResearchResult:
        blob = f"{payload.location or ''} {payload.query}".lower()
        note = "No mock local notes for this query."
        for needle, text in MOCK_NOTES.items():
            if needle in blob:
                note = text
                break
        return WebResearchResult(
            query=payload.query,
            hits=[
                WebResearchHit(
                    title=f"Mock {payload.kind} brief",
                    url="",
                    snippet=note,
                )
            ],
            notes=note,
            source_type=DataSourceType.mock,
        )


class RealWebResearchTool(Tool[WebResearchInput, WebResearchResult]):
    name = "web_research"
    description = "Live web search via Brave when SEARCH_API_KEY is set."
    input_model = WebResearchInput

    async def _run(self, payload: WebResearchInput) -> WebResearchResult:
        from app.tools.live_apis import brave_search

        q = payload.query
        if payload.location and payload.location.lower() not in q.lower():
            q = f"{q} {payload.location}"
        rows = await brave_search(q, count=payload.max_results)
        hits = [WebResearchHit(**row) for row in rows]
        notes = hits[0].snippet if hits else "No live search hits."
        return WebResearchResult(
            query=payload.query,
            hits=hits,
            notes=notes,
            source_type=DataSourceType.live,
        )
