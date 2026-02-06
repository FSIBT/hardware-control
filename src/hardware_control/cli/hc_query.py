"""CLI tool for querying and controlling hardware-control Apps.

Usage:
  hc-query get <query>... [--app=<name>] [--pid=<pid>] [--format=<fmt>]
  hc-query set <update>... [--app=<name>] [--pid=<pid>] [--format=<fmt>]
  hc-query config <file> [--app=<name>] [--pid=<pid>] [--format=<fmt>]
  hc-query list [--format=<fmt>]
  hc-query info [--app=<name>] [--pid=<pid>] [--format=<fmt>]
  hc-query (-h | --help)
  hc-query --version

Commands:
  get         Query parameter values (INSTRUMENT.PARAMETER)
  set         Set parameter values (INSTRUMENT.PARAMETER=VALUE)
  config      Execute commands from JSON config file
  list        List all running Apps
  info        Show App information

Options:
  --app=<name>      Name of the App to connect to
  --pid=<pid>       Process ID of the App to connect to
  --format=<fmt>    Output format: table, json, markdown, csv, sheets, compact [default: table]
  -h --help         Show this help message
  --version         Show version

Examples:
  hc-query list
  hc-query info --app BeamLineControl
  hc-query get PSU1.VOLTAGE PSU2.CURRENT
  hc-query set PSU1.VOLTAGE=42.5 PSU2.CURRENT=1.2
  hc-query get PSU1.VOLTAGE --format json
  hc-query config commands.json
"""

import json
import sys

from docopt import docopt

from ..remote import HardwareControlClient, discover_app, list_running_apps
from ..remote.formatters import (
    format_compact,
    format_csv,
    format_json,
    format_markdown,
    format_sheets,
    format_table,
)


def parse_query(query_str: str) -> dict:
    """Parse query string into dict.

    Args:
        query_str: String like "INSTRUMENT.PARAMETER"

    Returns:
        Dict with instrument and parameter keys
    """
    parts = query_str.split(".", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid query format: '{query_str}'. Expected INSTRUMENT.PARAMETER"
        )
    return {"instrument": parts[0], "parameter": parts[1]}


def parse_update(update_str: str) -> dict:
    """Parse update string into dict.

    Args:
        update_str: String like "INSTRUMENT.PARAMETER=VALUE"

    Returns:
        Dict with instrument, parameter, and value keys
    """
    if "=" not in update_str:
        raise ValueError(
            f"Invalid update format: '{update_str}'. Expected INSTRUMENT.PARAMETER=VALUE"
        )

    parts = update_str.split("=", 1)
    query = parse_query(parts[0])
    query["value"] = parts[1]
    return query


def format_output(data: dict, format_type: str) -> str:
    """Format response data for output.

    Args:
        data: Response dict from HardwareControlClient
        format_type: One of: table, json, markdown, csv, sheets, compact

    Returns:
        Formatted string
    """
    formatters = {
        "table": format_table,
        "json": format_json,
        "markdown": format_markdown,
        "csv": format_csv,
        "sheets": format_sheets,
        "compact": format_compact,
    }

    formatter = formatters.get(format_type)
    if not formatter:
        raise ValueError(
            f"Unknown format: {format_type}. "
            f"Valid formats: {', '.join(formatters.keys())}"
        )

    return formatter(data)


def cmd_list(args: dict) -> int:
    """List all running Apps.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    apps = list_running_apps()

    if not apps:
        print("No running hardware-control Apps found")
        return 0

    # Format as response for consistency
    response = {
        "status": "success",
        "data": [
            {
                "app_name": app["app_name"],
                "pid": app["pid"],
                "birth_time": app["birth_time"],
            }
            for app in apps
        ],
    }

    output = format_output(response, args["--format"])
    print(output)
    return 0


def cmd_info(args: dict) -> int:
    """Show App information.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Discover App
        app_name = args["--app"]
        pid = int(args["--pid"]) if args["--pid"] else None
        app_info = discover_app(app_name, pid)

        # Connect to App
        client = HardwareControlClient(
            ipc_address=app_info["ipc_address"],
            pid=app_info["pid"],
            app_name=app_info["app_name"],
        )

        # Get info
        response = client.get_app_info()
        client.close()

        # Format and print
        output = format_output(response, args["--format"])
        print(output)
        return 0

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_get(args: dict) -> int:
    """Query parameter values.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Parse queries
        queries = [parse_query(q) for q in args["<query>"]]

        # Discover App
        app_name = args["--app"]
        pid = int(args["--pid"]) if args["--pid"] else None
        app_info = discover_app(app_name, pid)

        # Connect to App
        client = HardwareControlClient(
            ipc_address=app_info["ipc_address"],
            pid=app_info["pid"],
            app_name=app_info["app_name"],
        )

        # Get parameters
        response = client.get_parameters(queries)
        client.close()

        # Format and print
        output = format_output(response, args["--format"])
        print(output)

        # Check for errors in response
        if response.get("status") == "error":
            return 1

        # Check if any individual queries had errors
        for item in response.get("data", []):
            if "error" in item:
                return 1

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_set(args: dict) -> int:
    """Set parameter values.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Parse updates
        updates = [parse_update(u) for u in args["<update>"]]

        # Discover App
        app_name = args["--app"]
        pid = int(args["--pid"]) if args["--pid"] else None
        app_info = discover_app(app_name, pid)

        # Connect to App
        client = HardwareControlClient(
            ipc_address=app_info["ipc_address"],
            pid=app_info["pid"],
            app_name=app_info["app_name"],
        )

        # Set parameters
        response = client.set_parameters(updates)
        client.close()

        # Format and print
        output = format_output(response, args["--format"])
        print(output)

        # Check for errors in response
        if response.get("status") == "error":
            return 1

        # Check if any individual updates had errors
        for item in response.get("data", []):
            if item.get("status") == "error":
                return 1

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_config(args: dict) -> int:
    """Execute commands from config file.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Read config file
        config_file = args["<file>"]
        with open(config_file) as f:
            config = json.load(f)

        # Discover App
        app_name = args["--app"]
        pid = int(args["--pid"]) if args["--pid"] else None
        app_info = discover_app(app_name, pid)

        # Connect to App
        client = HardwareControlClient(
            ipc_address=app_info["ipc_address"],
            pid=app_info["pid"],
            app_name=app_info["app_name"],
        )

        # Execute command from config
        command = config.get("command")
        if command == "get_parameters":
            response = client.get_parameters(config.get("queries", []))
        elif command == "set_parameters":
            response = client.set_parameters(config.get("updates", []))
        else:
            print(f"Error: Unknown command in config: {command}", file=sys.stderr)
            client.close()
            return 1

        client.close()

        # Format and print
        output = format_output(response, args["--format"])
        print(output)

        # Check for errors
        if response.get("status") == "error":
            return 1

        return 0

    except FileNotFoundError:
        print(f"Error: Config file not found: {args['<file>']}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for hc-query CLI."""
    args = docopt(__doc__, version="hc-query 1.0.0")

    # Dispatch to command handler
    if args["list"]:
        return cmd_list(args)
    elif args["info"]:
        return cmd_info(args)
    elif args["get"]:
        return cmd_get(args)
    elif args["set"]:
        return cmd_set(args)
    elif args["config"]:
        return cmd_config(args)
    else:
        print("Error: No command specified", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
