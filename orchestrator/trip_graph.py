from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
    NODE_INTAKE,
    NODE_PLANNER,
    NODE_CLARIFY,
    NODE_CITY_SELECTION,
    NODE_ATTRACTIONS,
    NODE_REPLAN,
    NODE_COMPOSE,
)
from schemas.trip_schema import TripState
from orchestrator import nodes


# Every node LangGraph can route to from ``planner`` — the conditional edge
# map is the identity function because ``PlannerAgent.decide_next`` returns
# the literal node name it wants executed next. LangGraph only coordinates
# execution here; the planner made the actual decision.
_ROUTABLE_NODES = [
    NODE_CLARIFY,
    NODE_CITY_SELECTION,
    NODE_ATTRACTIONS,
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
    NODE_REPLAN,
    NODE_COMPOSE,
]


def build_trip_graph():
    graph = StateGraph(TripState)

    graph.add_node(NODE_INTAKE, nodes.intake_node)
    graph.add_node(NODE_PLANNER, nodes.planner_node)
    graph.add_node(NODE_CLARIFY, nodes.clarify_node)
    graph.add_node(NODE_CITY_SELECTION, nodes.city_selection_node)
    graph.add_node(NODE_ATTRACTIONS, nodes.attractions_node)
    graph.add_node(AGENT_DESTINATION, nodes.destination_node)
    graph.add_node(AGENT_CLIMATE, nodes.climate_node)
    graph.add_node(AGENT_TRANSPORT, nodes.transport_node)
    graph.add_node(AGENT_HOTEL, nodes.hotel_node)
    graph.add_node(AGENT_ITINERARY, nodes.itinerary_node)
    graph.add_node(AGENT_BUDGET, nodes.budget_node)
    graph.add_node(NODE_REPLAN, nodes.replan_node)
    graph.add_node(NODE_COMPOSE, nodes.compose_node)

    graph.set_entry_point(NODE_INTAKE)
    graph.add_edge(NODE_INTAKE, NODE_PLANNER)

    graph.add_conditional_edges(
        NODE_PLANNER,
        lambda state: state["next_node"],
        {name: name for name in _ROUTABLE_NODES},
    )

    for worker_node in (
        NODE_CLARIFY,
        NODE_CITY_SELECTION,
        NODE_ATTRACTIONS,
        AGENT_DESTINATION,
        AGENT_CLIMATE,
        AGENT_TRANSPORT,
        AGENT_HOTEL,
        AGENT_ITINERARY,
        AGENT_BUDGET,
        NODE_REPLAN,
    ):
        graph.add_edge(worker_node, NODE_PLANNER)

    graph.add_edge(NODE_COMPOSE, END)

    return graph.compile(checkpointer=MemorySaver())


trip_graph = build_trip_graph()
