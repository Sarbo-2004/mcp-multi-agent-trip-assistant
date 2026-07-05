import asyncio
import json
import threading
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from schemas.mcp_schema import MCPToolResponse


class BaseMCPClient:
    """Shared Streamable-HTTP MCP client plumbing.

    Concrete clients (places, climate, transport, hotel) only declare their
    server URL/name and expose thin tool wrappers that delegate to
    ``call_tool``. All transport, async bridging and result parsing lives here
    so it is defined exactly once.
    """

    def __init__(self, server_url: str, server_name: str):
        self.server_url = self._ensure_mcp_suffix(server_url)
        self.server_name = server_name

    @staticmethod
    def _ensure_mcp_suffix(url: str) -> str:
        url = url.rstrip("/")

        if not url.endswith("/mcp"):
            url = f"{url}/mcp"

        return url

    def call_tool(
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
                error=f"Streamable HTTP MCP {self.server_name} client failed: {str(e)}",
                raw_response=str(e),
            )

    def health_check(self) -> Dict[str, Any]:
        try:
            tools = self._run_async(self._list_tools())

            return {
                "server_name": self.server_name,
                "server_url": self.server_url,
                "status": "healthy",
                "tools": tools,
            }

        except Exception as e:
            return {
                "server_name": self.server_name,
                "server_url": self.server_url,
                "status": "unhealthy",
                "error": str(e),
            }

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

    async def _list_tools(self) -> List[Dict[str, Any]]:
        async with streamablehttp_client(self.server_url) as transport:
            read_stream, write_stream, _ = transport

            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools_result = await session.list_tools()

                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                    }
                    for tool in tools_result.tools
                ]

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

        # A loop is already running on this thread (e.g. Streamlit). Run the
        # coroutine to completion on a dedicated thread to avoid nesting loops.
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
