import asyncio
import json
import threading
from typing import Any, Dict, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from config.settings import mcp_settings
from schemas.mcp_schema import MCPToolResponse


class TransportMCPClient:
    def __init__(self):
        self.server_url = mcp_settings.transport_mcp_url.rstrip("/")

        if not self.server_url.endswith("/mcp"):
            self.server_url = f"{self.server_url}/mcp"

    def get_transport_options(
        self,
        source: str,
        destination: str,
        mode: Optional[str] = "driving-car",
    ) -> MCPToolResponse:
        arguments: Dict[str, Any] = {
            "source": source,
            "destination": destination,
            "mode": mode or "driving-car",
        }

        return self._run_tool_sync(
            tool_name="get_transport_options",
            arguments=arguments,
        )

    def health_check(self) -> Dict[str, Any]:
        try:
            tools = self._run_async(self._list_tools())

            return {
                "server_name": "transport_mcp_server",
                "server_url": self.server_url,
                "status": "healthy",
                "tools": tools,
            }

        except Exception as e:
            return {
                "server_name": "transport_mcp_server",
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
                error=f"Streamable HTTP MCP transport client failed: {str(e)}",
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