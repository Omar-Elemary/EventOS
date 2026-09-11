from app.domain.models import EventRequirements, Logistics, LogisticsItem
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.wrapper import run_agent_node
from app.services.intake import weather_date
from app.services.research import research_weather, research_web


def _req(state: EventState) -> EventRequirements:
    raw = state["requirements"]
    return raw if isinstance(raw, EventRequirements) else EventRequirements.model_validate(raw)


async def _logic(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    date = weather_date(req)
    loc = req.location or "Cairo"
    weather, weather_cached = await research_weather(deps, loc, date, event_id=state.get("event_id"))
    local, local_cached = await research_web(
        deps,
        f"event transportation parking logistics {loc}",
        kind="logistics",
        location=loc,
        event_id=state.get("event_id"),
    )
    loc_l = loc.lower()
    if "hurghada" in loc_l:
        shuttle = "Airport shuttles every 30 min from HRG"
    elif "sharm" in loc_l:
        shuttle = "Airport shuttles every 30 min from SSH"
    elif "alexandria" in loc_l or "alex" in loc_l:
        shuttle = "Airport shuttles every 45 min from HBE / Borg El Arab"
    else:
        shuttle = "Airport shuttles every 30 min from CAI"
    items = [
        LogisticsItem(area="transportation", detail=shuttle, owner="CityLink Coaches"),
        LogisticsItem(area="parking", detail="On-site parking with overflow at adjacent lot", owner="venue"),
        LogisticsItem(area="equipment", detail="AV load-in 06:00; backup projector on site", owner="StageCraft AV Cairo"),
        LogisticsItem(area="staff", detail="Registration team of 8 plus 6 ushers", owner="EventCrew Staffing"),
        LogisticsItem(area="registration", detail="Badge printers x4; overflow queue barriers", owner="EventCrew Staffing"),
        LogisticsItem(area="catering", detail="Kitchen access 90 min before service; dietary labels", owner="Nile Bites Catering"),
        LogisticsItem(area="setup", detail="Day -1 evening pre-rig if venue allows", owner="venue"),
        LogisticsItem(area="teardown", detail="Same-night strike; storage hold overnight", owner="venue"),
    ]
    if local.notes:
        items.append(LogisticsItem(area="local_research", detail=local.notes, owner="research"))
    conflicts: list[str] = []
    if req.attendees >= 400:
        items.append(
            LogisticsItem(
                area="transportation",
                detail="Peak shuttle demand at close of day 1",
                conflict="Single loop may queue 20+ min",
                proposed_fix="Add a second coach at 17:00-18:30",
            )
        )
        conflicts.append("Shuttle capacity tight at day-1 close")
        items[-1].proposed_fix = "Add a second coach at 17:00-18:30"
    if weather.precipitation_chance >= 0.3:
        conflicts.append("Weather may affect outdoor transfer")
        items.append(
            LogisticsItem(
                area="transportation",
                detail="Covered drop-off preferred",
                proposed_fix="Use porte-cochere only; umbrellas at doors",
            )
        )
    if req.format == "outdoor":
        items.append(
            LogisticsItem(
                area="setup",
                detail="Outdoor site: ground protection, generator, and weather tent",
                owner="venue",
            )
        )
    origin = "cached" if weather_cached or local_cached else "fresh"
    logistics = Logistics(items=items, weather_summary=f"{weather.condition} ({weather.temp_c}C)", conflicts=conflicts)
    return {
        "logistics": logistics,
        "_output_summary": f"Logistics pack with {len(items)} items; weather={weather.condition} ({origin})",
    }


async def logistics_node(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    return await run_agent_node(
        "logistics",
        "Plan transport, staff, setup",
        state,
        deps,
        _logic,
        input_summary=f"{req.location}, {req.attendees} attendees",
    )
