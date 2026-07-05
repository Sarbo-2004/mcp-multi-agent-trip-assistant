from config.constants import AGENT_HOTEL
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.hotel_mcp_client import HotelMCPClient


class HotelAgent(BaseAgent):
    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_HOTEL,
            description="Fetches raw accommodation and stay-area data for a destination.",
            depends_on=[],
            output_key="hotel_result",
        )
        super().__init__(metadata)
        self.client = HotelMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        if not agent_input.destination:
            return self.error_response("Destination is required for hotel agent.")

        response = self.client.search_hotels(
            destination=agent_input.destination,
            budget=agent_input.budget,
            travelers=agent_input.travelers,
            limit=10,
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to fetch hotel data.",
                data={
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "destination": agent_input.destination,
                "budget": agent_input.budget,
                "travelers": agent_input.travelers,
                "raw_hotel_data": response.data,
                "raw_mcp_response": response.raw_response,
            },
            message="Raw hotel data fetched successfully.",
        )