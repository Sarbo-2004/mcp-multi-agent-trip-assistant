from typing import List, Optional

from schemas.trip_schema import TripRequest


class StateManager:
    """Detects cross-turn changes between a previous, completed trip request
    and a newly parsed one, and merges them into a single request for the
    planner to act on.

    This is turn-to-turn continuity (e.g. "actually make it 5 days instead")
    across separate planning runs — distinct from same-run automatic
    replanning, which ``PlannerAgent.apply_replan_directive`` handles when
    ``BudgetAgent`` reports infeasibility mid-plan.
    """

    COMPARABLE_FIELDS = [
        "source",
        "destination",
        "month",
        "days",
        "budget",
        "travelers",
        "travel_dates",
    ]

    def is_replan_candidate(
        self,
        current_request: TripRequest,
        previous_request: Optional[TripRequest],
    ) -> bool:
        if not previous_request:
            return False

        return bool(self.detect_modified_fields(previous_request, current_request))

    def detect_modified_fields(
        self,
        previous_request: TripRequest,
        current_request: TripRequest,
    ) -> List[str]:
        modified_fields = []

        for field_name in self.COMPARABLE_FIELDS:
            current_value = getattr(current_request, field_name)
            previous_value = getattr(previous_request, field_name)

            if current_value is not None and current_value != previous_value:
                modified_fields.append(field_name)

        if current_request.interests:
            previous_interests = sorted(previous_request.interests or [])
            current_interests = sorted(current_request.interests or [])

            if current_interests != previous_interests:
                modified_fields.append("interests")

        return modified_fields

    def merge_replan_request(
        self,
        previous_request: TripRequest,
        current_request: TripRequest,
    ) -> TripRequest:
        modified_fields = self.detect_modified_fields(previous_request, current_request)

        return TripRequest(
            user_query=current_request.user_query,
            source=current_request.source or previous_request.source,
            destination=current_request.destination or previous_request.destination,
            month=current_request.month or previous_request.month,
            days=current_request.days or previous_request.days,
            budget=current_request.budget or previous_request.budget,
            travelers=current_request.travelers or previous_request.travelers,
            interests=current_request.interests or previous_request.interests,
            travel_dates=current_request.travel_dates or previous_request.travel_dates,
            suggested_agents=[],
            missing_fields=[],
            confidence=max(current_request.confidence, previous_request.confidence),
            parser_used=f"replan_from_{current_request.parser_used}",
            turn_type="continuation",
            modified_fields=modified_fields,
            destination_scope=(
                current_request.destination_scope
                if "destination" in modified_fields
                else previous_request.destination_scope
            ),
        )
