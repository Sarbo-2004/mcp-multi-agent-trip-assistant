from dataclasses import asdict, fields
from typing import Any, Dict

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


def _sanitize_request_dict(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove fields not accepted by TripRequest.

    This prevents Redis memory keys or future extra fields from breaking:
    TripRequest(**request_dict)
    """

    allowed_fields = {field.name for field in fields(TripRequest)}

    return {
        key: value
        for key, value in (request_dict or {}).items()
        if key in allowed_fields
    }


def _request_from_state(state: TripState) -> TripRequest:
    request_dict = dict(state.get("request") or {})
    sanitized_request = _sanitize_request_dict(request_dict)
    state["request"] = sanitized_request

    return TripRequest(**sanitized_request)


def _base_agent_input(
    request: TripRequest,
    destination: Any = None,
    context: Dict[str, Any] = None,
) -> AgentInput:
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
# Intake
# ---------------------------------------------------------------------- #

def intake_node(state: TripState) -> TripState:
    """
    Parse raw query only when request was not already seeded by TripOrchestrator.

    Important for Redis memory:
    - TripOrchestrator loads Redis memory.
    - TripOrchestrator merges memory into request.
    - This node must not overwrite state["request"] when it already exists.
    """

    if not state.get("request"):
        parsed_request = asdict(
            intent_analyzer.analyze(state.get("raw_user_query", ""))
        )
        state["request"] = _sanitize_request_dict(parsed_request)
    else:
        state["request"] = _sanitize_request_dict(state.get("request") or {})

    state["trip_memory"] = state.get("trip_memory") or {}
    state["conversation_history"] = state.get("conversation_history") or []

    state["agent_results"] = {}
    state["errors"] = []

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
# Planner
# ---------------------------------------------------------------------- #

def planner_node(state: TripState) -> TripState:
    next_node = planner_agent.decide_next(state)
    state["next_node"] = next_node
    state["phase"] = planner_agent.phase_for_node(next_node)

    return state


# ---------------------------------------------------------------------- #
# Clarification
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
    """
    Free-text clarification answers may append raw text to the query.
    Re-run parser and fill only missing structured fields.

    This function does not erase Redis-merged fields.
    It only fills missing values from the reparsed query.
    """

    request_dict = dict(state.get("request") or {})
    query = request_dict.get("user_query") or state.get("raw_user_query", "")

    reparsed = asdict(intent_analyzer.analyze(query))
    reparsed = _sanitize_request_dict(reparsed)

    for field_name in (
        "source",
        "destination",
        "month",
        "days",
        "budget",
        "travelers",
        "interests",
        "destination_scope",
    ):
        if not request_dict.get(field_name) and reparsed.get(field_name):
            request_dict[field_name] = reparsed[field_name]

    state["request"] = _sanitize_request_dict(request_dict)

    agent_results = dict(state.get("agent_results") or {})

    if (
        AGENT_DESTINATION in agent_results
        and not agent_results[AGENT_DESTINATION].get("success")
    ):
        agent_results.pop(AGENT_DESTINATION, None)
        state["agent_results"] = agent_results


# ---------------------------------------------------------------------- #
# Destination
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
# Attractions
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
            context={
                "destination_mode": "fetch_attractions",
                "target_city": city,
            },
        )

        result = AGENT_REGISTRY[AGENT_DESTINATION].run(agent_input)

        if result.success:
            city_attractions[city] = result.data
        else:
            city_attractions[city] = {
                "ranked_places": [],
                "places": [],
                "error": result.error,
            }

            errors = list(state.get("errors") or [])
            errors.append(f"attractions:{city}: {result.error}")
            state["errors"] = errors

    state["city_attractions"] = city_attractions

    return state


# ---------------------------------------------------------------------- #
# Climate / Hotel helper
# ---------------------------------------------------------------------- #

def _run_per_city(state: TripState, agent_name: str, extra_context_fn) -> TripState:
    request = _request_from_state(state)

    selected_cities = state.get("selected_cities") or (
        [request.destination] if request.destination else []
    )

    per_city: Dict[str, Any] = {}
    overall_success = True

    for city in selected_cities:
        agent_input = _base_agent_input(
            request,
            destination=city,
            context=extra_context_fn(request),
        )

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
    return _run_per_city(
        state,
        AGENT_HOTEL,
        lambda request: {},
    )


# ---------------------------------------------------------------------- #
# Transport
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
# Budget
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
# Itinerary
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
# Replan
# ---------------------------------------------------------------------- #

def replan_node(state: TripState) -> TripState:
    planner_agent.apply_replan_directive(state)
    return state


# ---------------------------------------------------------------------- #
# Compose
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