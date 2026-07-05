from config.constants import AGENT_DESTINATION
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.places_mcp_client import PlacesMCPClient


class DestinationAgent(BaseAgent):
    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_DESTINATION,
            description="Recommends destinations or finds popular attractions for a selected destination.",
            depends_on=[],
            output_key="destination_result"
        )
        super().__init__(metadata)
        self.client = PlacesMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        if agent_input.destination:
            return self._get_places_for_destination(agent_input)

        return self._recommend_destinations(agent_input)

    def _get_places_for_destination(self, agent_input: AgentInput) -> AgentOutput:
        response = self.client.get_popular_places(
            destination=agent_input.destination,
            interests=agent_input.interests,
            limit=10
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to fetch destination places.",
                data={
                    "mode": "places_lookup",
                    "destination": agent_input.destination,
                    "raw_mcp_response": response.raw_response
                }
            )

        return self.success_response(
            data={
                "mode": "places_lookup",
                "destination": agent_input.destination,
                "interests": agent_input.interests,
                "places": response.data,
                "raw_mcp_response": response.raw_response
            },
            message="Popular places fetched successfully."
        )

    def _recommend_destinations(self, agent_input: AgentInput) -> AgentOutput:
        response = self.client.recommend_destinations(
            source=agent_input.source,
            interests=agent_input.interests,
            month=agent_input.month,
            budget=agent_input.budget,
            days=agent_input.days,
            travelers=agent_input.travelers,
            limit=8
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to recommend destinations.",
                data={
                    "mode": "destination_recommendation",
                    "source": agent_input.source,
                    "interests": agent_input.interests,
                    "month": agent_input.month,
                    "budget": agent_input.budget,
                    "days": agent_input.days,
                    "travelers": agent_input.travelers,
                    "raw_mcp_response": response.raw_response
                }
            )

        return self.success_response(
            data={
                "mode": "destination_recommendation",
                "source": agent_input.source,
                "interests": agent_input.interests,
                "month": agent_input.month,
                "budget": agent_input.budget,
                "days": agent_input.days,
                "travelers": agent_input.travelers,
                "recommended_destinations": response.data,
                "raw_mcp_response": response.raw_response
            },
            message="Destination recommendations generated successfully."
        )