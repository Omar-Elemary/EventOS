from app.domain.models import Schedule, ScheduleConflictResult, ScheduleItem
from app.tools.base import Tool


def detect_conflicts(schedule: Schedule) -> ScheduleConflictResult:
    items = [i.model_copy(deep=True) for i in schedule.items]
    by_id = {i.id: i for i in items}
    conflicts: list[str] = []

    for item in items:
        item.conflicts = []
        for dep in item.depends_on:
            pred = by_id.get(dep)
            if not pred:
                msg = f"{item.id} depends on missing {dep}"
                conflicts.append(msg)
                item.conflicts.append(msg)
                continue
            if item.start_time < pred.end_time:
                msg = f"{item.title} starts before dependency {pred.title} ends"
                conflicts.append(msg)
                item.conflicts.append(msg)

    for i, a in enumerate(items):
        for b in items[i + 1 :]:
            same_place = (a.location or "") == (b.location or "") and a.location
            overlap = a.start_time < b.end_time and b.start_time < a.end_time
            if same_place and overlap:
                msg = f"Overlap: {a.title} and {b.title} at {a.location}"
                conflicts.append(msg)
                a.conflicts.append(msg)
                b.conflicts.append(msg)

    return ScheduleConflictResult(conflicts=list(dict.fromkeys(conflicts)), items=items)


class ScheduleConflictCheckerTool(Tool[Schedule, ScheduleConflictResult]):
    name = "schedule_conflict_checker"
    description = "Detect overlapping sessions and broken dependencies."
    input_model = Schedule

    async def _run(self, payload: Schedule) -> ScheduleConflictResult:
        return detect_conflicts(payload)
