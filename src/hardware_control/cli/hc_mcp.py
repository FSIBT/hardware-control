"""MCP server for hardware-control Apps.

Provides LLM access to hardware-control Apps via the Model Context Protocol (MCP).

Usage:
  hc-mcp [--app=<name>] [--pid=<pid>]
  hc-mcp (-h | --help)
  hc-mcp --version

Options:
  --app=<name>      Name of the App to connect to
  --pid=<pid>       Process ID of the App to connect to
  -h --help         Show this help message
  --version         Show version
"""

import sys

from docopt import docopt

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError:
    print(
        "Error: MCP package not installed. Install with: pip install -e '.[mcp]'",
        file=sys.stderr,
    )
    sys.exit(1)

from ..remote import HardwareControlClient, discover_app

# Global client instance
client = None
app_name = ""


def create_server() -> Server:
    """Create and configure MCP server with tools.

    Returns:
        Configured MCP Server instance
    """
    server = Server("hardware-control")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools for hardware control."""
        return [
            Tool(
                name="list_instruments",
                description="List all instruments in the hardware-control App",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_parameters",
                description="Query parameter values from instruments. Returns current values for specified parameters.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "description": "List of queries to execute",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "instrument": {
                                        "type": "string",
                                        "description": "Instrument name",
                                    },
                                    "parameter": {
                                        "type": "string",
                                        "description": "Parameter name",
                                    },
                                },
                                "required": ["instrument", "parameter"],
                            },
                        }
                    },
                    "required": ["queries"],
                },
            ),
            Tool(
                name="set_parameters",
                description="Set parameter values on instruments. Use this to control hardware settings.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "updates": {
                            "type": "array",
                            "description": "List of parameter updates to execute",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "instrument": {
                                        "type": "string",
                                        "description": "Instrument name",
                                    },
                                    "parameter": {
                                        "type": "string",
                                        "description": "Parameter name",
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "Value to set (as string)",
                                    },
                                },
                                "required": ["instrument", "parameter", "value"],
                            },
                        }
                    },
                    "required": ["updates"],
                },
            ),
            Tool(
                name="list_parameters",
                description="List all parameters available for a specific instrument",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "instrument": {
                            "type": "string",
                            "description": "Instrument name",
                        }
                    },
                    "required": ["instrument"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls from LLM."""
        global client

        # Check if App is still alive
        if not client.is_alive():
            return [
                TextContent(
                    type="text",
                    text=f"Error: App '{app_name}' is no longer running. Please restart the hardware-control App.",
                )
            ]

        try:
            if name == "list_instruments":
                response = client.list_instruments()
                return [TextContent(type="text", text=str(response))]

            elif name == "get_parameters":
                queries = arguments.get("queries", [])
                response = client.get_parameters(queries)
                return [TextContent(type="text", text=str(response))]

            elif name == "set_parameters":
                updates = arguments.get("updates", [])
                response = client.set_parameters(updates)
                return [TextContent(type="text", text=str(response))]

            elif name == "list_parameters":
                instrument = arguments.get("instrument")
                response = client.list_parameters(instrument)
                return [TextContent(type="text", text=str(response))]

            else:
                return [TextContent(type="text", text=f"Error: Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    return server


def main() -> int:
    """Main entry point for hc-mcp server."""
    global client, app_name

    args = docopt(__doc__, version="hc-mcp 1.0.0")

    try:
        # Discover App
        app_name_arg = args["--app"]
        pid = int(args["--pid"]) if args["--pid"] else None
        app_info = discover_app(app_name_arg, pid)

        app_name = app_info["app_name"]

        # Create client
        client = HardwareControlClient(
            ipc_address=app_info["ipc_address"],
            pid=app_info["pid"],
            app_name=app_info["app_name"],
        )

        # Verify App is alive
        if not client.is_alive():
            print(f"Error: App '{app_name}' is not running", file=sys.stderr)
            return 1

        # Create and run server
        server = create_server()

        # Run stdio server (blocking)
        import asyncio

        asyncio.run(stdio_server(server))

        return 0

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    sys.exit(main())
