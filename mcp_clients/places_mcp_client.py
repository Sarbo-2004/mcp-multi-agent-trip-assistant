import asyncio
import json
import threading
from typing import Any, Dict, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from config.settings import mcp_settings
from schemas.mcp_schema import MCPToolResponse


class PlacesMCPClient:
    def __init__(self):
        self.server_url = mcp_settings.places_mcp_url

    def get_popular_places(
        self,
        destination: str,
        interests: Optional[list[str]] = None,
        limit: int = 10,
    ) -> MCPToolResponse:
        arguments: Dict[str, Any] = {
            "destination": destination,
            "interests": interests or [],
            "limit": limit,
        }

        return self._run_tool_sync(
            tool_name="get_popular_places",
            arguments=arguments,
        )

    def recommend_destinations(
        self,
        source: Optional[str] = None,
        interests: Optional[list[str]] = None,
        month: Optional[str] = None,
        budget: Optional[str] = None,
        days: Optional[int] = None,
        travelers: Optional[int] = None,
        limit: int = 8,
    ) -> MCPToolResponse:
        arguments: Dict[str, Any] = {
            "source": source,
            "interests": interests or [],
            "month": month,
            "budget": budget,
            "days": days,
            "travelers": travelers,
            "limit": limit,
        }

        return self._run_tool_sync(
            tool_name="recommend_destinations",
            arguments=arguments,
        )

    def health_check(self) -> Dict[str, Any]:
        try:
            tools = self._run_async(self._list_tools())

            return {
                "server_name": "places_mcp_server",
                "server_url": self.server_url,
                "status": "healthy",
                "tools": tools,
            }

        except Exception as e:
            return {
                "server_name": "places_mcp_server",
                "server_url": self.server_url,
                "status": "unhealthy",
                "error": str(e),
            }

    def _run_tool_sync(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPToolResponse:
        try:
            return self._run_async(
                self._call_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                )
            )

        except Exception as e:
            return MCPToolResponse(
                tool_name=tool_name,
                success=False,
                data={},
                error=f"Streamable HTTP MCP places client failed: {str(e)}",
                raw_response=str(e),
            )

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPToolResponse:
        async with streamablehttp_client(self.server_url) as transport:
            read_stream, write_stream, _ = transport

            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                result = await session.call_tool(
                    tool_name,
                    arguments=arguments,
                )

                parsed = self._parse_tool_result(result)

                success = bool(parsed.get("success", True))

                return MCPToolResponse(
                    tool_name=tool_name,
                    success=success,
                    data=parsed,
                    error=parsed.get("error"),
                    raw_response=parsed,
                )

    async def _list_tools(self) -> list[Dict[str, Any]]:
        async with streamablehttp_client(self.server_url) as transport:
            read_stream, write_stream, _ = transport

            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools_result = await session.list_tools()

                tools = []

                for tool in tools_result.tools:
                    tools.append(
                        {
                            "name": tool.name,
                            "description": tool.description,
                        }
                    )

                return tools

    def _parse_tool_result(self, result: Any) -> Dict[str, Any]:
        if hasattr(result, "content") and result.content:
            for item in result.content:
                text = getattr(item, "text", None)

                if text:
                    try:
                        return json.loads(text)
                    except Exception:
                        return {
                            "success": True,
                            "result": text,
                        }

        return {
            "success": True,
            "raw_result": str(result),
        }

    def _run_async(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        output = {}
        error = {}

        def runner():
            try:
                output["value"] = asyncio.run(coro)
            except Exception as e:
                error["value"] = e

        thread = threading.Thread(target=runner)
        thread.start()
        thread.join()

        if "value" in error:
            raise error["value"]

        return output.get("value")