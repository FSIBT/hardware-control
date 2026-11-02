"""MCP server for hardware-control Apps.

Provides LLM access to hardware-control Apps via the Model Context Protocol (MCP).

The App decides what is allowed: remote access needs to be turned on in the App
and its token, if it has one, needs to be set in the HC_TOKEN environment variable.

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

import asyncio
import json
import sys
import threading
import traceback
from importlib.metadata import version
from typing import Any

from docopt import docopt

try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    print(
        "Error: MCP package not installed. Install with: pip install 'hardware-control[mcp]'",
        file=sys.stderr,
    )
    sys.exit(1)

from ..remote import HardwareControlClient, discover_app

VALUE_SCHEMA = {"type": ["string", "number", "boolean"]}
INSTRUMENT_SCHEMA = {"type": "string", "description": "Instrument name"}


def schema(properties: dict | None = None) -> dict:
    """Create the input schema of a tool, where all properties are required."""
    properties = properties or {}
    return {"type": "object", "properties": properties, "required": list(properties)}


def list_schema(name: str, description: str, properties: dict) -> dict:
    """Create the input schema of a tool that takes a list of objects."""
    items = schema(properties)
    return schema({name: {"type": "array", "description": description, "items": items}})


READ_ANNOTATIONS = types.ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE_ANNOTATIONS = types.ToolAnnotations(
    read_only_hint=False, destructive_hint=True, open_world_hint=True
)

STATUS_TOOL = types.Tool(
    name="get_access_status",
    description="Show the access mode of the App: off, read-only or full. Only a person at the App can change it.",
    input_schema=schema(),
    annotations=READ_ANNOTATIONS,
)
READ_TOOLS = [
    types.Tool(
        name="list_instruments",
        description="List all instruments in the App.",
        input_schema=schema(),
        annotations=READ_ANNOTATIONS,
    ),
    types.Tool(
        name="list_parameters",
        description="List the parameters and commands of an instrument.",
        input_schema=schema({"instrument": INSTRUMENT_SCHEMA}),
        annotations=READ_ANNOTATIONS,
    ),
    types.Tool(
        name="get_parameters",
        description="Get the last values read from instruments. Values can be null if nothing was read yet.",
        input_schema=list_schema(
            "queries",
            "Parameters to read",
            {
                "instrument": INSTRUMENT_SCHEMA,
                "parameter": {"type": "string", "description": "Parameter name"},
            },
        ),
        annotations=READ_ANNOTATIONS,
    ),
]
WRITE_TOOLS = [
    types.Tool(
        name="set_parameters",
        description=(
            "Set parameters on real hardware. Each entry reports success (sent, "
            "not confirmed, so read the value back), deferred (e.g. ramping), "
            "skipped (dummy mode) or error."
        ),
        input_schema=list_schema(
            "updates",
            "Parameters to set",
            {
                "instrument": INSTRUMENT_SCHEMA,
                "parameter": {"type": "string", "description": "Parameter name"},
                "value": VALUE_SCHEMA,
            },
        ),
        annotations=WRITE_ANNOTATIONS,
    ),
    types.Tool(
        name="call_commands",
        description="Call commands on real hardware. Each entry reports success or error.",
        input_schema=list_schema(
            "commands",
            "Commands to call",
            {
                "instrument": INSTRUMENT_SCHEMA,
                "command": {"type": "string", "description": "Command name"},
            },
        ),
        annotations=WRITE_ANNOTATIONS,
    ),
]


def tools_for_mode(mode: str | None) -> list[types.Tool]:
    """List the tools that the access mode allows."""
    if mode == "read-only":
        return [STATUS_TOOL, *READ_TOOLS]
    if mode == "full":
        return [STATUS_TOOL, *READ_TOOLS, *WRITE_TOOLS]
    return [STATUS_TOOL]


def call_client(client: HardwareControlClient, name: str, arguments: dict) -> dict:
    """Run a tool with the client and return the response of the App."""
    if name == "get_access_status":
        return client.get_access_info()
    if name == "list_instruments":
        return client.list_instruments()
    if name == "list_parameters":
        return client.list_parameters(arguments.get("instrument"))
    if name == "get_parameters":
        return client.get_parameters(arguments.get("queries", []))
    if name == "set_parameters":
        return client.set_parameters(arguments.get("updates", []))
    if name == "call_commands":
        return client.call_commands(arguments.get("commands", []))
    return {"status": "error", "message": f"Unknown tool: {name}"}


def create_server(client: HardwareControlClient) -> Server:
    """Create the MCP server for a client that is connected to an App.

    The App enforces the access mode for each request, the list of tools only
    keeps the LLM from trying what will be refused.
    """
    # a ZMQ socket cannot be used by two threads at the same time
    lock = threading.Lock()

    def request(function, *args) -> Any:
        with lock:
            return function(*args)

    async def in_thread(function, *args) -> Any:
        return await asyncio.to_thread(request, function, *args)

    async def list_tools(ctx, params) -> types.ListToolsResult:
        """List the available tools, which can change with the access mode."""
        try:
            response = await in_thread(client.get_access_info)
            mode = response["data"]["access_mode"]
        except (RuntimeError, KeyError, TypeError):
            mode = None
        return types.ListToolsResult(tools=tools_for_mode(mode))

    async def call_tool(ctx, params) -> types.CallToolResult:
        """Run a tool and return the response of the App as JSON."""
        try:
            response = await in_thread(
                call_client, client, params.name, params.arguments or {}
            )
        except RuntimeError as e:
            response = {"status": "error", "message": str(e)}

        entries = response.get("data")
        failed = response.get("status") == "error" or (
            isinstance(entries, list)
            and any(isinstance(e, dict) and "error" in e for e in entries)
        )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(response))],
            structured_content=response,
            is_error=failed,
        )

    return Server(
        "hardware-control",
        version=version("hardware-control"),
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


async def run_server(server: Server) -> None:
    """Run MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def main() -> int:
    """Main entry point for hc-mcp server."""
    args = docopt(__doc__, version=f"hc-mcp {version('hardware-control')}")

    client = None
    try:
        pid = int(args["--pid"]) if args["--pid"] else None
        app_info = discover_app(args["--app"], pid)

        client = HardwareControlClient(
            ipc_address=app_info["ipc_address"],
            pid=app_info["pid"],
            app_name=app_info["app_name"],
        )

        asyncio.run(run_server(create_server(client)))
        return 0

    except ExceptionGroup as e:
        print("Unexpected error: unhandled errors in a TaskGroup", file=sys.stderr)
        for idx, sub in enumerate(e.exceptions, start=1):
            print(f"\nSub-exception {idx}:", file=sys.stderr)
            traceback.print_exception(sub, file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    sys.exit(main())
