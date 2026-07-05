from config.constants import AGENT_CLIMATE
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.climate_mcp_client import ClimateMCPClient


class ClimateAgent(BaseAgent):
    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_CLIMATE,
            description="Fetches raw structured climate data for a destination.",
            depends_on=[],
            output_key="climate_result",
        )
        super().__init__(metadata)
        self.client = ClimateMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        if not agent_input.destination:
            return self.error_response("Destination is required for climate agent.")

        response = self.client.get_climate(
            destination=agent_input.destination,
            month=agent_input.month,
            travel_dates=agent_input.context.get("travel_dates"),
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to fetch climate data.",
                data={
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "destination": agent_input.destination,
                "month": agent_input.month,
                "raw_climate_data": response.data,
                "raw_mcp_response": response.raw_response,
            },
            message="Raw climate data fetched successfully.",
        )