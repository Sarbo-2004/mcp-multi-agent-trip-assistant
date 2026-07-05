from typing import Dict, Optional

from config.settings import mcp_settings
from mcp_clients.base_mcp_client import BaseMCPClient
from schemas.mcp_schema import MCPToolResponse


class ClimateMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_url=mcp_settings.climate_mcp_url,
            server_name="climate_mcp_server",
        )

    def get_climate(
        self,
        destination: str,
        month: Optional[str] = None,
        travel_dates: Optional[Dict[str, str]] = None,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="get_climate",
            arguments={
                "destination": destination,
                "month": month,
                "travel_dates": travel_dates,
            },
        )
