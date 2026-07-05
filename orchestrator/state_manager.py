from dataclasses import asdict
from typing import Any, Dict, List, Optional

from schemas.trip_schema import TripContext, TripRequest


class StateManager:
    def is_replan_candidate(
        self,
        current_request: TripRequest,
        previous_context: Optional[TripContext],
    ) -> bool:
        if not previous_context:
            return False

        previous_request = previous_context.request

        if not previous_request:
            return False

        if current_request.parser_used == "context_continuation":
            return False

        changed_fields = self.detect_modified_fields(
            previous_request=previous_request,
            current_request=current_request,
        )

        if not changed_fields:
            return False

        if current_request.destination and current_request.destination != previous_request.destination:
            return True

        if previous_request.destination and not current_request.destination:
            return True

        return True

    def detect_modified_fields(
        self,
        previous_request: TripRequest,
        current_request: TripRequest,
    ) -> List:
        modified_fields = []

        comparable_fields = [
            "source",
            "destination",
            "month",
            "days",
            "budget",
            "travelers",
            "travel_dates",
        ]

        for field_name in comparable_fields:
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
        previous_context: TripContext,
        current_request: TripRequest,
    ) -> TripRequest:
        previous_request = previous_context.request

        modified_fields = self.detect_modified_fields(
            previous_request=previous_request,
            current_request=current_request,
        )

        merged_request = TripRequest(
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
            turn_type="replan",
            modified_fields=modified_fields,
        )

        return merged_request

    def needs_clarification(
        self,
        request: TripRequest,
        previous_context: Optional[TripContext] = None,
    ) -> bool:
        if previous_context:
            return False

        has_any_trip_signal = any(
            [
                request.source,
                request.destination,
                request.month,
                request.days,
                request.budget,
                request.travelers,
                request.interests,
            ]
        )

        if not has_any_trip_signal:
            return True

        if not request.destination and not request.interests:
            return True

        return False

    def build_clarification_questions(
        self,
        request: TripRequest,
    ) -> List:
        questions = []

        if not request.source:
            questions.append("Where will you be starting from?")

        if not request.destination and not request.interests:
            questions.append(
                "Do you already have a destination in mind, or should I recommend places based on your preferences?"
            )

        if not request.days:
            questions.append("How many days are you planning for?")

        if not request.month and not request.travel_dates:
            questions.append("Which month or travel period are you considering?")

        if not request.budget:
            questions.append("What budget range do you prefer: low, medium, or high?")

        return questions[:4]

    def build_clarification_response(
        self,
        request: TripRequest,
    ) -> Dict[str, Any]:
        questions = self.build_clarification_questions(request)

        return {
            "success": False,
            "status": "needs_clarification",
            "response": self._format_clarification_message(questions),
            "error": None,
            "request": asdict(request),
            "workflow": {
                "required_agents": [],
                "completed_agents": [],
                "failed_agents": [],
            },
            "summary": {
                "selected_destination": request.destination,
                "has_destination_recommendations": False,
                "destination_recommendations": [],
                "final_plan_summary": "More information is needed before planning can continue.",
                "errors": [],
            },
            "clarification_questions": questions,
        }

    def _format_clarification_message(self, questions: List[str]) -> str:
        if not questions:
            return "I need a little more information before planning this trip."

        lines = ["I can plan this, but I need a few details first:"]

        for index, question in enumerate(questions, start=1):
            lines.append(f"{index}. {question}")

        return "\n".join(lines)