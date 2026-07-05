from typing import Optional

from config.settings import mcp_settings
from mcp_clients.base_mcp_client import BaseMCPClient
from schemas.mcp_schema import MCPToolResponse


class HotelMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_url=mcp_settings.hotel_mcp_url,
            server_name="hotel_mcp_server",
        )

    def search_hotels(
        self,
        destination: str,
        budget: Optional[str] = None,
        travelers: Optional[int] = None,
        limit: int = 10,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="search_hotels",
            arguments={
                "destination": destination,
                "budget": budget,
                "travelers": travelers,
                "limit": limit,
            },
        )
