import requests
from typing import Dict, Any, Optional

from config.settings import network_settings
from schemas.mcp_schema import MCPToolRequest, MCPToolResponse


class BaseHTTPMCPClient:
    def __init__(self, base_url: str, server_name: str):
        self.base_url = base_url.rstrip("/")
        self.server_name = server_name
        self.timeout = network_settings.request_timeout
        self.ssl_verify = network_settings.ssl_verify

    def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> MCPToolResponse:
        if arguments is None:
            arguments = {}

        payload = MCPToolRequest(
            tool_name=tool_name,
            arguments=arguments
        )

        endpoint = f"{self.base_url}/tools/{tool_name}"

        try:
            response = requests.post(
                endpoint,
                json=payload.arguments,
                timeout=self.timeout,
                verify=self.ssl_verify
            )

            response.raise_for_status()

            try:
                result = response.json()
            except ValueError:
                return MCPToolResponse(
                    tool_name=tool_name,
                    success=False,
                    error="MCP server returned non-JSON response",
                    raw_response=response.text
                )

            return MCPToolResponse(
                tool_name=tool_name,
                success=True,
                data=result if isinstance(result, dict) else {"result": result},
                raw_response=result
            )

        except requests.exceptions.SSLError as e:
            return MCPToolResponse(
                tool_name=tool_name,
                success=False,
                error=(
                    "SSL verification failed. "
                    "If you are working behind a corporate proxy, "
                    "set SSL_VERIFY=false in your .env temporarily."
                ),
                raw_response=str(e)
            )

        except requests.exceptions.Timeout as e:
            return MCPToolResponse(
                tool_name=tool_name,
                success=False,
                error=f"Request timed out after {self.timeout} seconds",
                raw_response=str(e)
            )

        except requests.exceptions.ConnectionError as e:
            return MCPToolResponse(
                tool_name=tool_name,
                success=False,
                error=(
                    f"Could not connect to MCP server '{self.server_name}' "
                    f"at {self.base_url}. Make sure the server is running."
                ),
                raw_response=str(e)
            )

        except requests.exceptions.HTTPError as e:
            status_code = None
            response_text = None

            if e.response is not None:
                status_code = e.response.status_code
                response_text = e.response.text

            return MCPToolResponse(
                tool_name=tool_name,
                success=False,
                error=f"HTTP error from MCP server. Status code: {status_code}",
                raw_response=response_text or str(e)
            )

        except Exception as e:
            return MCPToolResponse(
                tool_name=tool_name,
                success=False,
                error=f"Unexpected MCP client error: {str(e)}",
                raw_response=str(e)
            )

    def health_check(self) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/health"

        try:
            response = requests.get(
                endpoint,
                timeout=self.timeout,
                verify=self.ssl_verify
            )

            response.raise_for_status()

            return {
                "server_name": self.server_name,
                "base_url": self.base_url,
                "status": "healthy",
                "response": response.json()
            }

        except Exception as e:
            return {
                "server_name": self.server_name,
                "base_url": self.base_url,
                "status": "unhealthy",
                "error": str(e)
            }