import math
from typing import Any, Dict, List

from config.constants import AGENT_BUDGET
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent


class BudgetAgent(BaseAgent):
    """Evaluates whether the requested trip is feasible — it does not build
    the plan itself.

    Feasibility has two independent checks:
      1. Time: does the requested number of days cover the selected cities
         plus the inter-city travel it takes to visit them?
      2. Cost: what would the trip roughly cost at the requested budget band,
         for context (not a hard pass/fail signal on its own).

    ``Replanning`` (a separate node) decides what to do when this agent
    reports ``feasible: False`` — this agent only judges, it never mutates
    the plan.
    """

    PER_DAY_ESTIMATES = {
        "low": 2500,
        "medium": 5000,
        "high": 10000,
    }

    MIN_DAYS_PER_CITY = 1.5
    TRAVEL_DAY_DISTANCE_THRESHOLD_KM = 250

    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_BUDGET,
            description="Evaluates trip feasibility (time and cost) without producing the plan itself.",
            depends_on=[],
            output_key="budget_result",
        )
        super().__init__(metadata)

    def run(self, agent_input: AgentInput) -> AgentOutput:
        available_days = agent_input.days or 3
        travelers = agent_input.travelers or 1
        budget_type = agent_input.budget or "medium"

        selected_cities = agent_input.context.get("selected_cities") or (
            [agent_input.destination] if agent_input.destination else []
        )
        inter_city_legs = agent_input.context.get("inter_city_legs") or []

        num_cities = max(len(selected_cities), 1)
        required_city_days = math.ceil(num_cities * self.MIN_DAYS_PER_CITY)
        travel_days = sum(
            1 for leg in inter_city_legs if self._leg_distance_km(leg) > self.TRAVEL_DAY_DISTANCE_THRESHOLD_KM
        )
        required_days = required_city_days + travel_days

        per_day = self.PER_DAY_ESTIMATES.get(budget_type, 5000)
        estimated_cost = per_day * max(required_days, available_days) * travelers

        feasible = required_days <= available_days

        suggested_adjustments: List[str] = []

        if not feasible:
            shortfall_days = required_days - available_days

            if num_cities > 1:
                suggested_adjustments.append(
                    f"Drop the lowest-priority city to reduce required days by roughly "
                    f"{math.ceil(self.MIN_DAYS_PER_CITY)}."
                )

            suggested_adjustments.append(
                f"Extend the trip by {shortfall_days} day(s) to comfortably cover {num_cities} "
                f"{'city' if num_cities == 1 else 'cities'}."
            )

        return self.success_response(
            data={
                "feasible": feasible,
                "available_days": available_days,
                "required_days": required_days,
                "num_cities": num_cities,
                "travel_days": travel_days,
                "budget_type": budget_type,
                "travelers": travelers,
                "estimated_cost_inr": estimated_cost,
                "breakdown": {
                    "stay": int(estimated_cost * 0.35),
                    "food": int(estimated_cost * 0.20),
                    "local_transport": int(estimated_cost * 0.20),
                    "activities": int(estimated_cost * 0.15),
                    "miscellaneous": int(estimated_cost * 0.10),
                },
                "suggested_adjustments": suggested_adjustments,
                "note": (
                    "This is a heuristic feasibility check, not a live pricing lookup. "
                    "Actual cost may vary by accommodation, transport mode, activity choices, and season."
                ),
            },
            message="Feasibility evaluated successfully." if feasible else "Trip is not feasible as requested.",
        )

    @staticmethod
    def _leg_distance_km(leg: Dict[str, Any]) -> float:
        transport_data = leg.get("transport_data") or {}

        for key in ("distance_km", "distance"):
            value = transport_data.get(key)

            if isinstance(value, (int, float)):
                return float(value)

        return 0.0
