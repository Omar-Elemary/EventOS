from langgraph.graph import END, START, StateGraph

from app.agents.budget import budget_node
from app.agents.critic import critic_node
from app.agents.finalize import finalize_node, human_review_node
from app.agents.logistics import logistics_node
from app.agents.requirements import orchestrator_node, requirements_node
from app.agents.risk import risk_node
from app.agents.schedule import schedule_node
from app.agents.venue import venue_node
from app.agents.vendor import vendor_node
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.routing import route_after_critic, route_after_orchestrator, route_after_venue


def _bind(fn, deps: GraphDeps):
    async def node(state: EventState):
        return await fn(state, deps)

    return node


def compile_graph(deps: GraphDeps):
    g = StateGraph(EventState)
    g.add_node("requirements", _bind(requirements_node, deps))
    g.add_node("orchestrator", _bind(orchestrator_node, deps))
    g.add_node("venue", _bind(venue_node, deps))
    g.add_node("vendor", _bind(vendor_node, deps))
    g.add_node("budget", _bind(budget_node, deps))
    g.add_node("schedule", _bind(schedule_node, deps))
    g.add_node("logistics", _bind(logistics_node, deps))
    g.add_node("risk", _bind(risk_node, deps))
    g.add_node("critic", _bind(critic_node, deps))
    g.add_node("finalize", _bind(finalize_node, deps))
    g.add_node("human_review", _bind(human_review_node, deps))

    g.add_edge(START, "requirements")
    g.add_edge("requirements", "orchestrator")
    g.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"venue": "venue", "end": END},
    )
    g.add_conditional_edges(
        "venue",
        route_after_venue,
        {"vendor": "vendor", "logistics": "logistics"},
    )
    g.add_edge("vendor", "budget")
    g.add_edge("budget", "schedule")
    g.add_edge("schedule", "logistics")
    g.add_edge("logistics", "risk")
    g.add_edge("risk", "critic")
    g.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "finalize": "finalize",
            "budget": "budget",
            "venue": "venue",
            "schedule": "schedule",
            "vendor": "vendor",
            "logistics": "logistics",
            "human": "human_review",
        },
    )
    g.add_edge("finalize", END)
    g.add_edge("human_review", END)
    return g.compile()
