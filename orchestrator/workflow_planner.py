from typing import List

from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
    AGENT_ORDER,
)
from schemas.trip_schema import TripRequest


class WorkflowPlanner:
    """Decides which agents (beyond destination resolution, which the graph
    always runs first) are needed for a resolved trip request.

    Destination scope/hierarchy is handled structurally by the graph
    (destination -> city_selection -> attractions nodes), so this planner no
    longer branches on ``destination_scope`` — by the time it runs, the
    destination has already been resolved to one or more concrete cities.
    """

    def plan(self, request: TripRequest) -> List[str]:
        if request.suggested_agents:
            return self._validate_and_order_agents(request.suggested_agents, request)

        return self._fallback_workflow(request)

    def _validate_and_order_agents(
        self,
        agents: List[str],
        request: TripRequest,
    ) -> List[str]:
        requested = set(agents)

        # ``request.source`` is authoritative for transport eligibility, even
        # though ``agents`` (e.g. Gemini's ``suggested_agents``) may have been
        # computed before a clarification answer supplied the source — this
        # planning step only ever runs once the missing_source_for_transport
        # clarification rule has already been resolved, so trust the field.
        if request.source:
            requested.add(AGENT_TRANSPORT)
        else:
            requested.discard(AGENT_TRANSPORT)

        ordered = [agent for agent in AGENT_ORDER if agent in requested]

        if AGENT_DESTINATION not in ordered:
            ordered.insert(0, AGENT_DESTINATION)

        return ordered

    def _fallback_workflow(self, request: TripRequest) -> List[str]:
        agents = [AGENT_DESTINATION]

        if request.month:
            agents.append(AGENT_CLIMATE)

        if request.source:
            agents.append(AGENT_TRANSPORT)

        agents.append(AGENT_HOTEL)
        agents.append(AGENT_ITINERARY)
        agents.append(AGENT_BUDGET)

        return self._validate_and_order_agents(agents, request)
