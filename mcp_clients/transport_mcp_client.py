from typing import Any, Dict, List, Optional

from config.settings import mcp_settings
from mcp_clients.base_mcp_client import BaseMCPClient
from schemas.mcp_schema import MCPToolResponse


class TransportMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_url=mcp_settings.transport_mcp_url,
            server_name="transport_mcp_server",
        )

    def get_transport_options(
        self,
        source: str,
        destination: str,
        mode: Optional[str] = "driving-car",
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="get_transport_options",
            arguments={
                "source": source,
                "destination": destination,
                "mode": mode or "driving-car",
            },
        )

    def optimize_route(
        self,
        points: List[Dict[str, Any]],
        start_index: int = 0,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="optimize_route",
            arguments={
                "points": points or [],
                "start_index": start_index,
            },
        )
