from typing import List, Optional

from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
)
from schemas.trip_schema import TripContext, TripRequest


class WorkflowPlanner:
    def plan(
        self,
        request: TripRequest,
        previous_context: Optional[TripContext] = None,
    ) -> List:
        if request.destination_scope == "state_or_region":
            agents = [AGENT_DESTINATION]

            if request.budget or request.days or request.travelers:
                agents.append(AGENT_BUDGET)

            return self._validate_and_order_agents(agents, request)

        if request.turn_type == "replan":
            return self._plan_replan(request, previous_context)

        if request.suggested_agents:
            return self._validate_and_order_agents(request.suggested_agents, request)

        return self._fallback_workflow(request)

    def _plan_replan(
        self,
        request: TripRequest,
        previous_context: Optional[TripContext],
    ) -> List:
        modified_fields = set(request.modified_fields or [])

        agents = []

        if "destination" in modified_fields:
            agents.extend(
                [
                    AGENT_DESTINATION,
                    AGENT_CLIMATE,
                    AGENT_TRANSPORT,
                    AGENT_HOTEL,
                    AGENT_ITINERARY,
                    AGENT_BUDGET,
                ]
            )

            return self._validate_and_order_agents(agents, request)

        if "source" in modified_fields:
            agents.append(AGENT_TRANSPORT)

        if "month" in modified_fields or "travel_dates" in modified_fields:
            agents.extend(
                [
                    AGENT_CLIMATE,
                    AGENT_ITINERARY,
                ]
            )

        if "days" in modified_fields:
            agents.extend(
                [
                    AGENT_ITINERARY,
                    AGENT_BUDGET,
                ]
            )

        if "budget" in modified_fields:
            agents.extend(
                [
                    AGENT_HOTEL,
                    AGENT_BUDGET,
                ]
            )

        if "travelers" in modified_fields:
            agents.extend(
                [
                    AGENT_HOTEL,
                    AGENT_BUDGET,
                ]
            )

        if "interests" in modified_fields:
            agents.extend(
                [
                    AGENT_DESTINATION,
                    AGENT_ITINERARY,
                ]
            )

        if not agents:
            agents = self._fallback_workflow(request)

        return self._validate_and_order_agents(agents, request)

    def _validate_and_order_agents(
        self,
        agents: List[str],
        request: TripRequest,
    ) -> List:
        preferred_order = [
            AGENT_DESTINATION,
            AGENT_CLIMATE,
            AGENT_TRANSPORT,
            AGENT_HOTEL,
            AGENT_ITINERARY,
            AGENT_BUDGET,
        ]

        valid_agents = set(preferred_order)

        ordered = []

        for agent in preferred_order:
            if agent in agents and agent in valid_agents and agent not in ordered:
                ordered.append(agent)

        if request.destination_scope == "state_or_region":
            blocked_agents = [
                AGENT_CLIMATE,
                AGENT_TRANSPORT,
                AGENT_HOTEL,
                AGENT_ITINERARY,
            ]

            ordered = [
                agent
                for agent in ordered
                if agent not in blocked_agents
            ]

            if AGENT_DESTINATION not in ordered:
                ordered.insert(0, AGENT_DESTINATION)

            return ordered

        if AGENT_TRANSPORT in ordered:
            if not request.source or not request.destination:
                ordered.remove(AGENT_TRANSPORT)

        if not request.destination:
            if AGENT_DESTINATION not in ordered:
                ordered.insert(0, AGENT_DESTINATION)

        return ordered

    def _fallback_workflow(self, request: TripRequest) -> List:
        agents = []

        if request.destination or not request.destination:
            agents.append(AGENT_DESTINATION)

        if request.destination and request.month:
            agents.append(AGENT_CLIMATE)

        if request.source and request.destination:
            agents.append(AGENT_TRANSPORT)

        if request.destination:
            agents.append(AGENT_HOTEL)

        if request.destination and request.days:
            agents.append(AGENT_ITINERARY)

        if request.budget or request.days or request.travelers:
            agents.append(AGENT_BUDGET)

        return self._validate_and_order_agents(agents, request)