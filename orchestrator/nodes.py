from dataclasses import asdict
from typing import Any, Dict, List

from langgraph.types import interrupt

from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
    PHASE_INTAKE,
    PHASE_DONE,
)
from schemas.agent_schema import AgentInput, AgentOutput
from schemas.trip_schema import TripRequest, TripState

from orchestrator.intent_analyzer import IntentAnalyzer
from orchestrator.planner_agent import PlannerAgent
from orchestrator.final_response_composer import FinalResponseComposer

from agents_mcp.destination_agent import DestinationAgent
from agents_mcp.climate_agent import ClimateAgent
from agents_mcp.transport_agent import TransportAgent
from agents_mcp.hotel_agent import HotelAgent
from agents_mcp.itinerary_agent import ItineraryAgent
from agents_mcp.budget_agent import BudgetAgent


# Shared singletons. LangGraph nodes are plain functions, so the stateful
# collaborators they need (the planner brain, agent instances, the intent
# parser, the composer) live at module scope and are imported by
# ``trip_graph.py`` to wire the graph.
intent_analyzer = IntentAnalyzer()
planner_agent = PlannerAgent()
final_response_composer = FinalResponseComposer()

AGENT_REGISTRY = {
    AGENT_DESTINATION: DestinationAgent(),
    AGENT_CLIMATE: ClimateAgent(),
    AGENT_TRANSPORT: TransportAgent(),
    AGENT_HOTEL: HotelAgent(),
    AGENT_ITINERARY: ItineraryAgent(),
    AGENT_BUDGET: BudgetAgent(),
}


def _record_result(state: TripState, agent_name: str, result: AgentOutput) -> None:
    agent_results = dict(state.get("agent_results") or {})
    agent_results[agent_name] = asdict(result)
    state["agent_results"] = agent_results

    if not result.success:
        errors = list(state.get("errors") or [])
        errors.append(f"{agent_name}: {result.error}")
        state["errors"] = errors


def _request_from_state(state: TripState) -> TripRequest:
    return TripRequest(**state["request"])


def _base_agent_input(request: TripRequest, destination: Any = None, context: Dict[str, Any] = None) -> AgentInput:
    return AgentInput(
        query=request.user_query,
        source=request.source,
        destination=destination if destination is not None else request.destination,
        month=request.month,
        days=request.days,
        budget=request.budget,
        travelers=request.travelers,
        interests=request.interests,
        context=context or {},
    )


# ---------------------------------------------------------------------- #
# Intake — parses the raw query into a TripRequest exactly once per thread.
# If the facade has already seeded ``state["request"]`` (e.g. a merged
# continuation request), intake leaves it untouched.
# ---------------------------------------------------------------------- #

def intake_node(state: TripState) -> TripState:
    # ``intake`` only ever runs once, at the start of a brand-new graph
    # invocation (never on resume, since ``Command(resume=...)`` continues
    # execution from inside the paused node, not from the entry point). The
    # facade may pre-seed ``request`` itself (e.g. a merged continuation
    # request); when it hasn't, parse the raw query here.
    if not state.get("request"):
        state["request"] = asdict(intent_analyzer.analyze(state.get("raw_user_query", "")))

    state["agent_results"] = {}
    state["errors"] = []
    state["conversation_history"] = state.get("conversation_history") or []
    state["phase"] = PHASE_INTAKE
    state["pending_clarification"] = None
    state["clarification_answers"] = {}
    state["asked_clarifications"] = []
    state["planned_agents"] = []
    state["destination_resolved"] = False
    state["selected_cities"] = []
    state["city_recommendations"] = []
    state["city_attractions"] = {}
    state["travel_sequence"] = None
    state["feasible"] = None
    state["replan_count"] = 0
    state["replan_directives"] = []
    state["final_response"] = None
    state["done"] = False

    return state


# ---------------------------------------------------------------------- #
# Planner hub — the only node that decides where to go next.
# ---------------------------------------------------------------------- #

def planner_node(state: TripState) -> TripState:
    next_node = planner_agent.decide_next(state)
    state["next_node"] = next_node
    state["phase"] = planner_agent.phase_for_node(next_node)

    return state


# ---------------------------------------------------------------------- #
# Clarification — generic, rule-driven. Re-derives the same question
# deterministically before and after the interrupt (validated LangGraph
# pattern: the node re-runs from the top on resume, so recomputation before
# ``interrupt()`` is harmless and avoids reconstructing dataclasses from a
# checkpointed dict).
# ---------------------------------------------------------------------- #

def clarify_node(state: TripState) -> TripState:
    clarification = planner_agent.build_clarification(state)
    state["pending_clarification"] = asdict(clarification)

    answer = interrupt(state["pending_clarification"])

    planner_agent.merge_clarification_answer(state, clarification, answer)

    if not state.get("destination_resolved"):
        _reparse_request_after_clarification(state)

    return state


def city_selection_node(state: TripState) -> TripState:
    clarification = planner_agent.build_city_selection(state)
    state["pending_clarification"] = asdict(clarification)

    answer = interrupt(state["pending_clarification"])

    planner_agent.merge_clarification_answer(state, clarification, answer)

    return state


def _reparse_request_after_clarification(state: TripState) -> None:
    """Free-text clarification answers (e.g. the ambiguous-request rule)
    only append raw text to the query. Re-run the intent parser on the
    combined text so structured fields (destination, days, ...) actually
    get filled in, then drop the stale failed destination result so the
    planner retries it instead of looping back to ``clarify`` forever.
    """

    request_dict = dict(state.get("request") or {})
    query = request_dict.get("user_query") or state.get("raw_user_query", "")

    reparsed = asdict(intent_analyzer.analyze(query))

    for field_name in (
        "source", "destination", "month", "days", "budget",
        "travelers", "interests", "destination_scope",
    ):
        if not request_dict.get(field_name) and reparsed.get(field_name):
            request_dict[field_name] = reparsed[field_name]

    state["request"] = request_dict

    agent_results = dict(state.get("agent_results") or {})

    if AGENT_DESTINATION in agent_results and not agent_results[AGENT_DESTINATION].get("success"):
        agent_results.pop(AGENT_DESTINATION, None)
        state["agent_results"] = agent_results


# ---------------------------------------------------------------------- #
# Destination — scope resolution / city recommendation / no-destination
# recommendation. Never fetches attractions itself.
# ---------------------------------------------------------------------- #

def destination_node(state: TripState) -> TripState:
    request = _request_from_state(state)
    agent_input = _base_agent_input(request)

    result = AGENT_REGISTRY[AGENT_DESTINATION].run(agent_input)
    _record_result(state, AGENT_DESTINATION, result)

    if not result.success:
        return state

    mode = result.data.get("mode")

    if mode == "scope_resolved":
        state["selected_cities"] = result.data.get("resolved_cities", [])
        state["destination_resolved"] = True

    elif mode == "city_recommendation":
        state["city_recommendations"] = result.data.get("city_recommendations", [])
        state["destination_resolved"] = True

    elif mode == "destination_recommendation":
        recommended = result.data.get("recommended_destinations") or {}
        state["city_recommendations"] = recommended.get("recommendations", [])
        state["destination_resolved"] = True

    return state


# ---------------------------------------------------------------------- #
# Attractions — fetched and ranked separately for each selected city.
# Never fetches for the whole region.
# ---------------------------------------------------------------------- #

def attractions_node(state: TripState) -> TripState:
    request = _request_from_state(state)
    city_attractions = dict(state.get("city_attractions") or {})
    selected_cities = state.get("selected_cities") or []

    for city in selected_cities:
        if city in city_attractions:
            continue

        agent_input = _base_agent_input(
            request,
            destination=city,
            context={"destination_mode": "fetch_attractions", "target_city": city},
        )

        result = AGENT_REGISTRY[AGENT_DESTINATION].run(agent_input)

        if result.success:
            city_attractions[city] = result.data
        else:
            city_attractions[city] = {"ranked_places": [], "places": [], "error": result.error}
            errors = list(state.get("errors") or [])
            errors.append(f"attractions:{city}: {result.error}")
            state["errors"] = errors

    state["city_attractions"] = city_attractions

    return state


# ---------------------------------------------------------------------- #
# Climate / Hotel — single-destination agents, looped per selected city and
# aggregated. The agents themselves are unchanged.
# ---------------------------------------------------------------------- #

def _run_per_city(state: TripState, agent_name: str, extra_context_fn) -> TripState:
    request = _request_from_state(state)
    selected_cities = state.get("selected_cities") or (
        [request.destination] if request.destination else []
    )

    per_city: Dict[str, Any] = {}
    overall_success = True

    for city in selected_cities:
        agent_input = _base_agent_input(request, destination=city, context=extra_context_fn(request))
        result = AGENT_REGISTRY[agent_name].run(agent_input)
        per_city[city] = asdict(result)

        if not result.success:
            overall_success = False

    output = AgentOutput(
        agent_name=agent_name,
        success=overall_success,
        data={"by_city": per_city},
        message=(
            f"{agent_name} data fetched for all cities."
            if overall_success
            else f"{agent_name} failed for one or more cities."
        ),
        error=None if overall_success else "One or more cities failed.",
    )
    _record_result(state, agent_name, output)

    return state


def climate_node(state: TripState) -> TripState:
    return _run_per_city(
        state,
        AGENT_CLIMATE,
        lambda request: {"travel_dates": request.travel_dates},
    )


def hotel_node(state: TripState) -> TripState:
    return _run_per_city(state, AGENT_HOTEL, lambda request: {})


# ---------------------------------------------------------------------- #
# Transport — intra-city order, city order, final travel sequence.
# ---------------------------------------------------------------------- #

def transport_node(state: TripState) -> TripState:
    request = _request_from_state(state)
    agent_input = _base_agent_input(
        request,
        context={
            "city_attractions": state.get("city_attractions") or {},
            "selected_cities": state.get("selected_cities") or [],
        },
    )

    result = AGENT_REGISTRY[AGENT_TRANSPORT].run(agent_input)
    _record_result(state, AGENT_TRANSPORT, result)

    if result.success:
        state["travel_sequence"] = result.data

    return state


# ---------------------------------------------------------------------- #
# Budget — feasibility only.
# ---------------------------------------------------------------------- #

def budget_node(state: TripState) -> TripState:
    request = _request_from_state(state)
    transport_result = (state.get("agent_results") or {}).get(AGENT_TRANSPORT) or {}
    inter_city_legs = (transport_result.get("data") or {}).get("inter_city_legs") or []

    agent_input = _base_agent_input(
        request,
        context={
            "selected_cities": state.get("selected_cities") or [],
            "inter_city_legs": inter_city_legs,
        },
    )

    result = AGENT_REGISTRY[AGENT_BUDGET].run(agent_input)
    _record_result(state, AGENT_BUDGET, result)

    if result.success:
        state["feasible"] = result.data.get("feasible")

    return state


# ---------------------------------------------------------------------- #
# Itinerary — multi-city skeleton.
# ---------------------------------------------------------------------- #

def itinerary_node(state: TripState) -> TripState:
    request = _request_from_state(state)
    agent_input = _base_agent_input(
        request,
        context={
            "selected_cities": state.get("selected_cities") or [],
            "city_attractions": state.get("city_attractions") or {},
        },
    )

    result = AGENT_REGISTRY[AGENT_ITINERARY].run(agent_input)
    _record_result(state, AGENT_ITINERARY, result)

    return state


# ---------------------------------------------------------------------- #
# Replan — applies one directive and clears the agent results it invalidates.
# ---------------------------------------------------------------------- #

def replan_node(state: TripState) -> TripState:
    planner_agent.apply_replan_directive(state)

    return state


# ---------------------------------------------------------------------- #
# Compose — terminal node.
# ---------------------------------------------------------------------- #

def compose_node(state: TripState) -> TripState:
    state["final_response"] = final_response_composer.compose(state)
    state["done"] = True
    state["phase"] = PHASE_DONE

    return state


NODE_FUNCTIONS = {
    AGENT_DESTINATION: destination_node,
    AGENT_CLIMATE: climate_node,
    AGENT_TRANSPORT: transport_node,
    AGENT_HOTEL: hotel_node,
    AGENT_ITINERARY: itinerary_node,
    AGENT_BUDGET: budget_node,
}
