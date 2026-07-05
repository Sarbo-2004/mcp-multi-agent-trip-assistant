from config.constants import AGENT_TRANSPORT
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.transport_mcp_client import TransportMCPClient


class TransportAgent(BaseAgent):
    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_TRANSPORT,
            description="Fetches raw transport distance and duration between source and destination.",
            depends_on=[],
            output_key="transport_result",
        )
        super().__init__(metadata)
        self.client = TransportMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        if not agent_input.source:
            return self.error_response("Source is required for transport agent.")

        if not agent_input.destination:
            return self.error_response("Destination is required for transport agent.")

        response = self.client.get_transport_options(
            source=agent_input.source,
            destination=agent_input.destination,
            mode="driving-car",
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to fetch transport data.",
                data={
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "source": agent_input.source,
                "destination": agent_input.destination,
                "raw_transport_data": response.data,
                "raw_mcp_response": response.raw_response,
            },
            message="Raw transport data fetched successfully.",
        )