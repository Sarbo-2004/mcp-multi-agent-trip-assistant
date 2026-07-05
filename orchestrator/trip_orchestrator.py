from dataclasses import asdict
from typing import Any, Dict, Optional

from orchestrator.dynamic_executor import DynamicExecutor
from orchestrator.final_response_composer import FinalResponseComposer
from orchestrator.intent_analyzer import IntentAnalyzer
from orchestrator.state_manager import StateManager
from orchestrator.workflow_planner import WorkflowPlanner
from schemas.trip_schema import FinalTripPlan, TripContext, TripRequest


class TripOrchestrator:
    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.workflow_planner = WorkflowPlanner()
        self.dynamic_executor = DynamicExecutor()
        self.final_response_composer = FinalResponseComposer()
        self.state_manager = StateManager()
        self.last_context: Optional[TripContext] = None

    def run(
        self,
        user_query: str,
        previous_context: Optional[TripContext] = None,
        debug: bool = False,
    ) -> Dict[str, Any]:
        active_previous_context = previous_context or self.last_context

        if self._is_destination_continuation(user_query, active_previous_context):
            request = self._build_continuation_request(
                user_query=user_query,
                previous_context=active_previous_context,
            )
        else:
            parsed_request = self.intent_analyzer.analyze(user_query)

            if self.state_manager.is_replan_candidate(
                current_request=parsed_request,
                previous_context=active_previous_context,
            ):
                request = self.state_manager.merge_replan_request(
                    previous_context=active_previous_context,
                    current_request=parsed_request,
                )
            else:
                request = parsed_request

        if self.state_manager.needs_clarification(
            request=request,
            previous_context=active_previous_context,
        ):
            request.turn_type = "clarification_needed"
            request.clarification_questions = self.state_manager.build_clarification_questions(request)
            return self.state_manager.build_clarification_response(request)

        required_agents = self.workflow_planner.plan(
            request=request,
            previous_context=active_previous_context,
        )

        context = TripContext(
            request=request,
            extracted_entities=asdict(request),
            required_agents=required_agents,
            agent_results={},
            errors=[],
            conversation_history=self._build_conversation_history(
                previous_context=active_previous_context,
                user_query=user_query,
            ),
            pending_clarifications=[],
            last_user_action=request.turn_type,
        )

        context = self.dynamic_executor.execute(context)

        self.last_context = context

        final_plan = self._compose_final_plan(context)
        composed_response = self.final_response_composer.compose(context)

        if debug:
            return self._build_debug_response(
                request=request,
                required_agents=required_agents,
                context=context,
                final_plan=final_plan,
                composed_response=composed_response,
            )

        return self._build_clean_response(
            request=request,
            required_agents=required_agents,
            context=context,
            final_plan=final_plan,
            composed_response=composed_response,
        )

    def _build_conversation_history(
        self,
        previous_context: Optional[TripContext],
        user_query: str,
    ) -> list:
        history = []

        if previous_context:
            history.extend(previous_context.conversation_history or [])

            history.append(
                {
                    "role": "system_state",
                    "request": asdict(previous_context.request),
                }
            )

        history.append(
            {
                "role": "user",
                "content": user_query,
            }
        )

        return history[-10:]

    def _build_clean_response(
        self,
        request: TripRequest,
        required_agents: list,
        context: TripContext,
        final_plan: FinalTripPlan,
        composed_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        destination_recommendations = self._extract_destination_recommendations_from_context(context)

        return {
            "success": composed_response.get("success", False),
            "response": composed_response.get("response"),
            "error": composed_response.get("error"),
            "request": {
                "source": request.source,
                "destination": request.destination,
                "month": request.month,
                "days": request.days,
                "budget": request.budget,
                "travelers": request.travelers,
                "interests": request.interests,
                "parser_used": request.parser_used,
                "turn_type": request.turn_type,
                "modified_fields": request.modified_fields,
            },
            "workflow": {
                "required_agents": required_agents,
                "completed_agents": self._get_completed_agents(context),
                "failed_agents": self._get_failed_agents(context),
            },
            "summary": {
                "selected_destination": request.destination,
                "has_destination_recommendations": bool(destination_recommendations),
                "destination_recommendations": destination_recommendations,
                "final_plan_summary": final_plan.summary,
                "errors": context.errors,
            },
        }

    def _build_debug_response(
        self,
        request: TripRequest,
        required_agents: list,
        context: TripContext,
        final_plan: FinalTripPlan,
        composed_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "request": asdict(request),
            "required_agents": required_agents,
            "agent_results": {
                agent_name: asdict(result)
                for agent_name, result in context.agent_results.items()
            },
            "errors": context.errors,
            "final_plan": asdict(final_plan),
            "composed_response": composed_response,
            "conversation_history": context.conversation_history,
        }

    def _get_completed_agents(self, context: TripContext) -> list:
        completed = []

        for agent_name, result in context.agent_results.items():
            if result.success:
                completed.append(agent_name)

        return completed

    def _get_failed_agents(self, context: TripContext) -> list:
        failed = []

        for agent_name, result in context.agent_results.items():
            if not result.success:
                failed.append(
                    {
                        "agent": agent_name,
                        "error": result.error,
                    }
                )

        return failed

    def _extract_destination_recommendations_from_context(
        self,
        context: TripContext,
    ) -> list:
        destination_result = context.agent_results.get("destination_agent")

        if not destination_result or not destination_result.success:
            return []

        data = destination_result.data or {}

        if data.get("mode") != "destination_recommendation":
            return []

        recommended_destinations = data.get("recommended_destinations", {})
        recommendations = recommended_destinations.get("recommendations", [])

        clean_recommendations = []

        for item in recommendations:
            if not isinstance(item, dict):
                continue

            clean_recommendations.append(
                {
                    "destination": item.get("destination"),
                    "state_or_region": item.get("state_or_region"),
                    "match_score": item.get("match_score"),
                    "best_for": item.get("best_for"),
                    "reason": item.get("reason"),
                    "ideal_days": item.get("ideal_days"),
                    "budget_fit": item.get("budget_fit"),
                    "travel_note": item.get("travel_note"),
                }
            )

        return clean_recommendations

    def _is_destination_continuation(
        self,
        user_query: str,
        previous_context: Optional[TripContext],
    ) -> bool:
        if not previous_context:
            return False

        query = user_query.lower().strip()

        recommendations = self._extract_recommended_destinations(previous_context)

        if recommendations:
            for destination in recommendations:
                if destination.lower() in query:
                    return True

        continuation_phrases = [
            "continue with",
            "go with",
            "select",
            "choose",
            "finalize",
            "proceed with",
            "plan for",
            "let's go with",
            "lets go with",
        ]

        if any(phrase in query for phrase in continuation_phrases):
            return True

        return False

    def _build_continuation_request(
        self,
        user_query: str,
        previous_context: TripContext,
    ) -> TripRequest:
        previous_request = previous_context.request
        selected_destination = self._extract_selected_destination(
            user_query=user_query,
            previous_context=previous_context,
        )

        return TripRequest(
            user_query=user_query,
            source=previous_request.source,
            destination=selected_destination,
            month=previous_request.month,
            days=previous_request.days,
            budget=previous_request.budget,
            travelers=previous_request.travelers,
            interests=previous_request.interests,
            travel_dates=previous_request.travel_dates,
            suggested_agents=[
                "destination_agent",
                "climate_agent",
                "transport_agent",
                "hotel_agent",
                "itinerary_agent",
                "budget_agent",
            ],
            missing_fields=[],
            confidence=0.95,
            parser_used="context_continuation",
            turn_type="continue_with_destination",
            modified_fields=["destination"],
        )

    def _extract_selected_destination(
        self,
        user_query: str,
        previous_context: TripContext,
    ) -> Optional:
        query = user_query.lower()

        recommendations = self._extract_recommended_destinations(previous_context)

        for destination in recommendations:
            if destination.lower() in query:
                return destination

        cleaned_query = query

        removable_phrases = [
            "continue with",
            "go with",
            "select",
            "choose",
            "finalize",
            "proceed with",
            "plan for",
            "let's go with",
            "lets go with",
        ]

        for phrase in removable_phrases:
            cleaned_query = cleaned_query.replace(phrase, "")

        cleaned_query = cleaned_query.strip(" .,!")

        if cleaned_query:
            return cleaned_query.title()

        return None

    def _extract_recommended_destinations(
        self,
        context: TripContext,
    ) -> list:
        destination_result = context.agent_results.get("destination_agent")

        if not destination_result or not destination_result.success:
            return []

        data = destination_result.data or {}
        recommended_destinations = data.get("recommended_destinations", {})
        recommendations = recommended_destinations.get("recommendations", [])

        destinations = []

        for item in recommendations:
            if isinstance(item, dict):
                destination = item.get("destination")

                if destination:
                    destinations.append(destination)

        return destinations

    def _compose_final_plan(self, context: TripContext) -> FinalTripPlan:
        request = context.request

        sections = {}

        for agent_name, result in context.agent_results.items():
            sections[agent_name] = {
                "success": result.success,
                "message": result.message,
                "data": result.data,
                "error": result.error,
            }

        if context.errors:
            summary = (
                f"Trip planning completed with some issues for "
                f"{request.destination or 'the recommended destination'}."
            )
        else:
            if request.destination:
                summary = f"Trip planning completed successfully for {request.destination}."
            else:
                summary = "Destination recommendations generated successfully."

        return FinalTripPlan(
            query=request.user_query,
            destination=request.destination,
            summary=summary,
            sections=sections,
            errors=context.errors,
        )