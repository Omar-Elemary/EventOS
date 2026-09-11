from app.domain.enums import IssueType, RiskSeverity, VendorCategory
from app.domain.models import Risk, RiskCheckerInput
from app.tools.base import Tool


def _risk(
    *,
    title: str,
    severity: RiskSeverity,
    probability: float,
    impact: str,
    description: str,
    explanation: str,
    solutions: list[str],
    issue_type: IssueType,
    owner: str,
    trigger: str | None = None,
) -> Risk:
    return Risk(
        title=title,
        severity=severity,
        probability=probability,
        impact=impact,
        description=description,
        explanation=explanation,
        solutions=solutions,
        mitigation="; ".join(solutions),
        ai_recommendation=" ".join(f"{i}. {s}" for i, s in enumerate(solutions, 1)),
        issue_type=issue_type,
        owner=owner,
        trigger=trigger or description[:180],
    )


def evaluate_risks(payload: RiskCheckerInput) -> list[Risk]:
    risks: list[Risk] = []
    req = payload.requirements
    selected = next((v for v in payload.venues if v.selected), payload.venues[0] if payload.venues else None)
    loc = (req.location if req else None) or "this city"
    attendees = int(req.attendees) if req else 0

    if req and not selected:
        risks.append(
            _risk(
                title="No venue locked",
                severity=RiskSeverity.critical,
                probability=0.9,
                impact="There is nowhere confirmed to host the program, so contracts and invitations cannot go out.",
                description="The plan has no selected venue.",
                explanation=(
                    f"A {attendees or 'large'}-person event in {loc} still has no hall on the plan. "
                    "Without a venue you cannot lock catering, AV load-in, or guest communications."
                ),
                solutions=[
                    "Ask the planner to search again with a broader area or a nearby city.",
                    "Add a venue manually if you already have a hold.",
                    "Reduce headcount if every local hall is too small.",
                ],
                issue_type=IssueType.venue_capacity,
                owner="Venue lead",
            )
        )

    if req and selected and selected.capacity < req.attendees:
        risks.append(
            _risk(
                title="Venue capacity shortfall",
                severity=RiskSeverity.critical,
                probability=0.95,
                impact="Guests cannot be seated; fire-code and experience failure on the door.",
                description=f"{selected.name} holds {selected.capacity} vs {req.attendees} attendees.",
                explanation=(
                    f"{selected.name} is listed at {selected.capacity} people, but the brief is {req.attendees}. "
                    "Overflow usually shows up as door queues, standing-room-only sessions, and a possible safety stop."
                ),
                solutions=[
                    f"Switch to a hall that seats at least {req.attendees} (plus ~10% staff/walk-ins).",
                    "Cap registration at the venue limit and move overflow to a live stream or overflow room.",
                    "Split the program across two rooms if the venue has breakout space.",
                ],
                issue_type=IssueType.venue_capacity,
                owner="Venue lead",
                trigger=f"Capacity {selected.capacity} < {req.attendees}",
            )
        )

    if payload.budget and payload.budget.remaining < -1:
        overrun = abs(payload.budget.remaining)
        cur = payload.budget.currency
        risks.append(
            _risk(
                title="Budget overrun",
                severity=RiskSeverity.high if overrun < payload.budget.total_budget * 0.15 else RiskSeverity.critical,
                probability=0.9,
                impact="You cannot sign venue/vendor contracts without extra funds or cuts.",
                description=f"Plan is over budget by {overrun:.0f} {cur}.",
                explanation=(
                    f"Line items plus 10% contingency exceed the cap by {overrun:,.0f} {cur}. "
                    "The usual drivers are venue rental, catering per person, and AV. "
                    "Leaving this open means deposits bounce or quality gets cut on show week."
                ),
                solutions=[
                    f"Raise the live budget by at least {overrun:,.0f} {cur} (use the planner chip).",
                    "Pick a cheaper venue that still fits capacity.",
                    "Drop non-core packages first: entertainment, lighting, videography, then trim catering/AV.",
                    "Ask two vendors in the same category for a lower-tier quote.",
                ],
                issue_type=IssueType.budget,
                owner="Finance",
                trigger=f"Remaining {payload.budget.remaining:.0f} {cur}",
            )
        )
    elif payload.budget and payload.budget.total_budget > 0:
        headroom = payload.budget.remaining / payload.budget.total_budget
        if 0 <= headroom <= 0.03:
            risks.append(
                _risk(
                    title="Budget tightness",
                    severity=RiskSeverity.low,
                    probability=0.45,
                    impact="Any late add-on (extra coaches, overtime AV) will break the cap.",
                    description=f"Only {payload.budget.remaining:,.0f} {payload.budget.currency} remains after contingency.",
                    explanation=(
                        f"The plan fits, but almost every {payload.budget.currency} is allocated. "
                        "A 50-person walk-in, a generator, or overtime crew would push you over."
                    ),
                    solutions=[
                        "Hold a 5–8% owner reserve outside the published budget.",
                        "Freeze new line items unless something else is cut.",
                        "Get written quotes so estimates do not drift before lock.",
                    ],
                    issue_type=IssueType.budget,
                    owner="Finance",
                )
            )

    if payload.schedule and payload.schedule.conflicts:
        risks.append(
            _risk(
                title="Schedule conflicts",
                severity=RiskSeverity.high,
                probability=0.8,
                impact="Overlapping sessions or broken setup mean a late start or a dark stage.",
                description="; ".join(payload.schedule.conflicts[:3]),
                explanation=(
                    "Two activities share a room or a session starts before its setup finishes. "
                    "That is how registration blocks AV, or teardown starts while guests are still in the hall."
                ),
                solutions=[
                    "Put registration, coffee, and networking in the foyer — keep the hall for sessions only.",
                    "Finish AV setup before doors; do not overlap rehearsal with keynote.",
                    "Move teardown after the last guest moment, not during reception.",
                ],
                issue_type=IssueType.schedule,
                owner="Stage manager",
            )
        )

    cats = {v.category for v in payload.vendors if v.selected}
    needed = {
        VendorCategory.catering,
        VendorCategory.av,
        VendorCategory.security,
        VendorCategory.photography,
        VendorCategory.staffing,
    }
    missing = needed - cats
    if missing:
        labels = ", ".join(sorted(m.value for m in missing))
        risks.append(
            _risk(
                title="Incomplete vendor coverage",
                severity=RiskSeverity.medium,
                probability=0.7,
                impact="Show-day gaps: no food, no mics, no door control, or no ushers.",
                description=f"Missing categories: {labels}.",
                explanation=(
                    f"The plan still has no selected vendor for: {labels}. "
                    "These are core, not nice-to-have. Gaps here become last-minute market rates."
                ),
                solutions=[
                    "Source the missing categories before sending invitations.",
                    "Add a preferred vendor manually if you already have a relationship.",
                    "Ask the planner to search a broader set (Continue without is only for non-core extras).",
                ],
                issue_type=IssueType.vendors,
                owner="Vendor lead",
            )
        )

    if payload.weather and payload.weather.precipitation_chance >= 0.3:
        risks.append(
            _risk(
                title="Weather disruption",
                severity=RiskSeverity.medium,
                probability=payload.weather.precipitation_chance,
                impact="Outdoor transfer, branding, and open-air program can fail in rain or wind.",
                description=payload.weather.notes or payload.weather.condition,
                explanation=(
                    f"Forecast for {payload.weather.location} on {payload.weather.date}: "
                    f"{payload.weather.condition} with about {int(payload.weather.precipitation_chance * 100)}% rain chance. "
                    "The indoor program can still run; the risk is arrivals, outdoor photo, and uncovered load-in."
                ),
                solutions=[
                    "Keep registration and sessions indoor; use a covered drop-off only.",
                    "Hold a weather tent / umbrellas at doors if any outdoor moment stays on the rundown.",
                    "Move outdoor branding and VIP photos to a foyer backup.",
                ],
                issue_type=IssueType.logistics,
                owner="Logistics",
            )
        )

    if payload.logistics and payload.logistics.conflicts:
        fix = next((i.proposed_fix for i in payload.logistics.items if i.proposed_fix), None)
        risks.append(
            _risk(
                title="Logistics conflicts",
                severity=RiskSeverity.medium,
                probability=0.6,
                impact="Guests queue for shuttles or trucks block the load-in bay.",
                description="; ".join(payload.logistics.conflicts[:3]),
                explanation=(
                    f"At {attendees or 'this'} headcount, a single shuttle loop or one load-in window is usually too thin. "
                    "The plan already flags: " + "; ".join(payload.logistics.conflicts[:3]) + ". "
                    "This does not block approval, but it will show up at close of day if ignored."
                ),
                solutions=[
                    fix or "Add a second coach for the peak 90 minutes at close.",
                    "Stagger load-in: AV first, then catering, then décor — one owner on the dock.",
                    "Publish a guest shuttle timetable on badges and the event WhatsApp.",
                ],
                issue_type=IssueType.logistics,
                owner="Logistics",
            )
        )

    if req and selected and selected.capacity < req.attendees * 1.1 and selected.capacity >= req.attendees:
        risks.append(
            _risk(
                title="Limited capacity headroom",
                severity=RiskSeverity.low,
                probability=0.4,
                impact="Walk-ins, crew, and press cannot be absorbed without crowding.",
                description=f"{selected.name} is within 10% of {req.attendees} attendees.",
                explanation=(
                    f"{selected.name} fits the guest list ({selected.capacity} seats for {req.attendees} people) "
                    "but leaves little room for staff, security, and last-minute plus-ones."
                ),
                solutions=[
                    "Cap public registration at ~90% of hall capacity.",
                    "Hold a small overflow / standing room or a simulcast foyer.",
                    "Badge staff separately so they do not consume guest seats.",
                ],
                issue_type=IssueType.venue_capacity,
                owner="Registration",
            )
        )

    return risks


class RiskCheckerTool(Tool[RiskCheckerInput, list[Risk]]):
    name = "risk_checker"
    description = "Rule-based risk scan over the current plan."
    input_model = RiskCheckerInput

    async def _run(self, payload: RiskCheckerInput) -> list[Risk]:
        return evaluate_risks(payload)
