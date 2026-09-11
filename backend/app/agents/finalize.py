from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.wrapper import run_agent_node
from app.services.serialize import snapshot_state


async def _logic(state: EventState, deps: GraphDeps) -> dict:
    status = state.get("status") or "approved"
    if deps.persist_plan:
        await deps.persist_plan(snapshot_state(state) | {"status": status})
    await deps.sink.emit(
        state["event_id"],
        {"type": "plan_completed", "status": status, "run_id": state["run_id"]},
    )
    return {"status": status, "_output_summary": f"Persisted plan status={status}"}


async def finalize_node(state: EventState, deps: GraphDeps) -> dict:
    return await run_agent_node(
        "finalize",
        "Persist approved plan",
        state,
        deps,
        _logic,
        input_summary="Write EventPlan to database",
    )


async def human_review_node(state: EventState, deps: GraphDeps) -> dict:
    async def _h(s: EventState, d: GraphDeps) -> dict:
        if d.persist_plan:
            await d.persist_plan(snapshot_state(s) | {"status": "needs_human_review"})
        await d.sink.emit(
            s["event_id"],
            {"type": "plan_completed", "status": "needs_human_review", "run_id": s["run_id"]},
        )
        return {
            "status": "needs_human_review",
            "_output_summary": "Iteration cap reached; best plan retained for human review",
        }

    return await run_agent_node(
        "human_review",
        "Stop replanning and keep best plan",
        state,
        deps,
        _h,
        input_summary="MAX_ITERATIONS exceeded",
    )
