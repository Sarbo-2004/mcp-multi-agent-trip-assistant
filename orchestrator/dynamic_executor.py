from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
)
from schemas.agent_schema import AgentInput, AgentOutput
from schemas.trip_schema import TripContext

from agents_mcp.destination_agent import DestinationAgent
from agents_mcp.climate_agent import ClimateAgent
from agents_mcp.transport_agent import TransportAgent
from agents_mcp.hotel_agent import HotelAgent


class DynamicExecutor:
    def __init__(self):
        self.agent_registry = {
            AGENT_DESTINATION: DestinationAgent(),
            AGENT_CLIMATE: ClimateAgent(),
            AGENT_TRANSPORT: TransportAgent(),
            AGENT_HOTEL: HotelAgent(),
        }

    def execute(self, context: TripContext) -> TripContext:
        for agent_name in context.required_agents:
            if not self._can_run_agent(agent_name, context):
                result = self._skipped_response(agent_name, context)
                context.agent_results[agent_name] = result
                continue

            if agent_name in [AGENT_ITINERARY, AGENT_BUDGET]:
                result = self._run_local_agent(agent_name, context)
            else:
                result = self._run_mcp_agent(agent_name, context)

            context.agent_results[agent_name] = result

            if not result.success:
                context.errors.append(f"{agent_name}: {result.error}")

        return context

    def _can_run_agent(self, agent_name: str, context: TripContext) -> bool:
        request = context.request

        if agent_name == AGENT_DESTINATION:
            return True

        if request.destination_scope == "state_or_region":
            if agent_name in [
                AGENT_CLIMATE,
                AGENT_TRANSPORT,
                AGENT_HOTEL,
                AGENT_ITINERARY,
            ]:
                return False

        if agent_name == AGENT_TRANSPORT:
            return bool(request.source and request.destination)

        if agent_name in [AGENT_CLIMATE, AGENT_HOTEL, AGENT_ITINERARY]:
            return bool(request.destination)

        if agent_name == AGENT_BUDGET:
            return True

        return True

    def _skipped_response(self, agent_name: str, context: TripContext) -> AgentOutput:
        request = context.request

        if request.destination_scope == "state_or_region":
            reason = (
                f"{agent_name} skipped because '{request.destination}' is a broad region/state. "
                "A specific city, town, or route should be selected first before running this agent."
            )

        elif agent_name == AGENT_TRANSPORT:
            reason = "Transport agent skipped because both source and destination are required."

        elif agent_name in [AGENT_CLIMATE, AGENT_HOTEL, AGENT_ITINERARY]:
            reason = (
                f"{agent_name} skipped because destination is not available yet. "
                "Run destination recommendation first, then continue planning after destination selection."
            )

        else:
            reason = f"{agent_name} skipped because required information is missing."

        return AgentOutput(
            agent_name=agent_name,
            success=False,
            data={
                "skipped": True,
                "source": request.source,
                "destination": request.destination,
                "destination_scope": request.destination_scope,
                "missing_fields": request.missing_fields,
            },
            message=reason,
            error=reason,
        )

    def _run_mcp_agent(self, agent_name: str, context: TripContext) -> AgentOutput:
        agent = self.agent_registry.get(agent_name)

        if not agent:
            return AgentOutput(
                agent_name=agent_name,
                success=False,
                error=f"Agent '{agent_name}' is not registered.",
            )

        request = context.request

        agent_input = AgentInput(
            query=request.user_query,
            source=request.source,
            destination=request.destination,
            month=request.month,
            days=request.days,
            budget=request.budget,
            travelers=request.travelers,
            interests=request.interests,
            context={
                "agent_results": context.agent_results,
                "travel_dates": request.travel_dates,
                "missing_fields": request.missing_fields,
                "destination_scope": request.destination_scope,
            },
        )

        return agent.run(agent_input)

    def _run_local_agent(self, agent_name: str, context: TripContext) -> AgentOutput:
        if agent_name == AGENT_ITINERARY:
            return self._generate_itinerary(context)

        if agent_name == AGENT_BUDGET:
            return self._estimate_budget(context)

        return AgentOutput(
            agent_name=agent_name,
            success=False,
            error=f"Local agent '{agent_name}' is not implemented.",
        )

    def _generate_itinerary(self, context: TripContext) -> AgentOutput:
        request = context.request

        if not request.destination:
            return AgentOutput(
                agent_name=AGENT_ITINERARY,
                success=False,
                data={
                    "destination": None,
                    "missing_fields": ["destination"],
                },
                message="Itinerary generation skipped because destination is not selected yet.",
                error="Destination is required to generate itinerary.",
            )

        if request.destination_scope == "state_or_region":
            return AgentOutput(
                agent_name=AGENT_ITINERARY,
                success=False,
                data={
                    "destination": request.destination,
                    "destination_scope": request.destination_scope,
                    "reason": "Destination is a broad region/state.",
                },
                message=(
                    "Itinerary generation skipped because a specific city, town, "
                    "or route must be selected first."
                ),
                error="Specific destination is required to generate itinerary.",
            )

        days = request.days or 3

        itinerary_skeleton = []

        for day in range(1, days + 1):
            itinerary_skeleton.append(
                {
                    "day": day,
                    "structure": [
                        "morning_activity",
                        "afternoon_activity",
                        "evening_activity",
                    ],
                    "context_required": [
                        "destination_places",
                        "climate_data",
                        "transport_data",
                        "hotel_signals",
                        "user_interests",
                    ],
                    "notes": (
                        "This is an itinerary skeleton only. "
                        "The final response composer should generate actual activities using all raw agent outputs."
                    ),
                }
            )

        return AgentOutput(
            agent_name=AGENT_ITINERARY,
            success=True,
            data={
                "destination": request.destination,
                "destination_scope": request.destination_scope,
                "days": days,
                "itinerary_type": "skeleton",
                "itinerary": itinerary_skeleton,
            },
            message="Itinerary skeleton generated successfully.",
        )

    def _estimate_budget(self, context: TripContext) -> AgentOutput:
        request = context.request

        days = request.days or 3
        travelers = request.travelers or 1
        budget_type = request.budget or "medium"

        per_day_estimates = {
            "low": 2500,
            "medium": 5000,
            "high": 10000,
        }

        per_day = per_day_estimates.get(budget_type, 5000)
        total = per_day * days * travelers

        return AgentOutput(
            agent_name=AGENT_BUDGET,
            success=True,
            data={
                "budget_type": budget_type,
                "days": days,
                "travelers": travelers,
                "estimated_cost_inr": total,
                "breakdown": {
                    "stay": int(total * 0.35),
                    "food": int(total * 0.20),
                    "local_transport": int(total * 0.20),
                    "activities": int(total * 0.15),
                    "miscellaneous": int(total * 0.10),
                },
                "note": (
                    "This is a rough deterministic budget estimate. "
                    "Actual cost may vary by accommodation, transport mode, activity choices, and season."
                ),
            },
            message="Budget estimated successfully.",
        )