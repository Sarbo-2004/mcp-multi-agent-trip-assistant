from typing import Any, Dict, List

from config.constants import AGENT_ITINERARY
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent


class ItineraryAgent(BaseAgent):
    """Builds a deterministic day-wise itinerary skeleton, grouped by city.

    The skeleton is intentionally content-free: the final response composer
    fills each slot using the raw outputs of the other agents (ranked
    per-city attractions, climate, transport, hotel, budget). This keeps
    itinerary business logic (day allocation across cities) inside an agent
    rather than in the orchestrator, while leaving actual content generation
    to the composer.
    """

    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_ITINERARY,
            description="Generates a day-wise itinerary skeleton grouped by city.",
            depends_on=[],
            output_key="itinerary_result",
        )
        super().__init__(metadata)

    def run(self, agent_input: AgentInput) -> AgentOutput:
        selected_cities = agent_input.context.get("selected_cities") or (
            [agent_input.destination] if agent_input.destination else []
        )

        if not selected_cities:
            return self.error_response(
                error="At least one resolved city is required to generate an itinerary.",
                data={"missing_fields": ["destination"]},
            )

        total_days = agent_input.days or 3
        city_attractions = agent_input.context.get("city_attractions") or {}

        days_per_city = self._allocate_days(selected_cities, total_days, city_attractions)

        city_plans: List[Dict[str, Any]] = []
        day_counter = 1

        for city in selected_cities:
            days_for_city = days_per_city.get(city, 0)

            day_plans = [
                {
                    "day": day_counter + offset,
                    "city": city,
                    "structure": ["morning_activity", "afternoon_activity", "evening_activity"],
                    "context_required": [
                        "ranked_city_attractions",
                        "climate_data",
                        "transport_data",
                        "hotel_signals",
                        "user_interests",
                    ],
                }
                for offset in range(days_for_city)
            ]

            city_plans.append({
                "city": city,
                "days": days_for_city,
                "day_plans": day_plans,
                "notes": (
                    "This is an itinerary skeleton only. The final response composer should "
                    "generate actual day content using this city's ranked attractions."
                ),
            })

            day_counter += days_for_city

        return self.success_response(
            data={
                "selected_cities": selected_cities,
                "total_days": total_days,
                "itinerary_type": "multi_city_skeleton",
                "city_plans": city_plans,
            },
            message="Multi-city itinerary skeleton generated successfully.",
        )

    @staticmethod
    def _allocate_days(
        selected_cities: List[str],
        total_days: int,
        city_attractions: Dict[str, Any],
    ) -> Dict[str, int]:
        num_cities = len(selected_cities)

        if num_cities == 0:
            return {}

        base_days = max(total_days // num_cities, 1)
        allocation = {city: base_days for city in selected_cities}

        remaining_days = total_days - (base_days * num_cities)

        for city in selected_cities:
            if remaining_days <= 0:
                break

            allocation[city] += 1
            remaining_days -= 1

        return allocation
