"""Output formatting utilities for hardware-control query responses."""

import csv
import io
import json

from rich.console import Console
from rich.table import Table


def format_table(data: dict) -> str:
    """Format response as a Rich table (human-readable).

    Args:
        data: Response dict from HardwareControlClient

    Returns:
        Formatted string for terminal display
    """
    console = Console()

    # Handle error responses
    if data.get("status") == "error":
        return f"Error: {data.get('message', 'Unknown error')}"

    response_data = data.get("data", [])

    # Handle different data types
    if isinstance(response_data, list) and len(response_data) > 0:
        if isinstance(response_data[0], dict):
            # List of dicts (get/set parameters)
            table = Table(show_header=True, header_style="bold magenta")

            # Determine columns from first item
            keys = list(response_data[0].keys())
            for key in keys:
                table.add_column(key.replace("_", " ").title())

            # Add rows
            for item in response_data:
                table.add_row(*[str(item.get(key, "")) for key in keys])

            # Capture table output
            with console.capture() as capture:
                console.print(table)
            return capture.get()
        else:
            # Simple list (instruments, parameters)
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Item")

            for item in response_data:
                table.add_row(str(item))

            with console.capture() as capture:
                console.print(table)
            return capture.get()

    elif isinstance(response_data, dict):
        # Dict response (app_info)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Key")
        table.add_column("Value")

        for key, value in response_data.items():
            # Format lists nicely
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            table.add_row(key.replace("_", " ").title(), str(value))

        with console.capture() as capture:
            console.print(table)
        return capture.get()

    return str(response_data)


def format_json(data: dict) -> str:
    """Format response as pretty JSON.

    Args:
        data: Response dict from HardwareControlClient

    Returns:
        Pretty-printed JSON string
    """
    return json.dumps(data, indent=2)


def format_markdown(data: dict) -> str:
    """Format response as a Markdown table.

    Args:
        data: Response dict from HardwareControlClient

    Returns:
        Markdown-formatted table string
    """
    if data.get("status") == "error":
        return f"**Error:** {data.get('message', 'Unknown error')}"

    response_data = data.get("data", [])

    if isinstance(response_data, list) and len(response_data) > 0:
        if isinstance(response_data[0], dict):
            # List of dicts
            keys = list(response_data[0].keys())

            # Header
            header = "| " + " | ".join(k.replace("_", " ").title() for k in keys) + " |"
            separator = "| " + " | ".join("---" for _ in keys) + " |"

            # Rows
            rows = []
            for item in response_data:
                row = "| " + " | ".join(str(item.get(k, "")) for k in keys) + " |"
                rows.append(row)

            return "\n".join([header, separator] + rows)
        else:
            # Simple list
            lines = ["| Item |", "| --- |"]
            lines.extend(f"| {item} |" for item in response_data)
            return "\n".join(lines)

    elif isinstance(response_data, dict):
        # Dict response
        lines = ["| Key | Value |", "| --- | --- |"]
        for key, value in response_data.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"| {key.replace('_', ' ').title()} | {value} |")
        return "\n".join(lines)

    return str(response_data)


def format_sheets(data: dict) -> str:
    """Format response as TSV for Google Sheets.

    Args:
        data: Response dict from HardwareControlClient

    Returns:
        Tab-separated values string
    """
    if data.get("status") == "error":
        return f"Error\t{data.get('message', 'Unknown error')}"

    response_data = data.get("data", [])

    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t")

    if isinstance(response_data, list) and len(response_data) > 0:
        if isinstance(response_data[0], dict):
            # List of dicts
            keys = list(response_data[0].keys())
            writer.writerow(keys)
            for item in response_data:
                writer.writerow([item.get(k, "") for k in keys])
        else:
            # Simple list
            writer.writerow(["Item"])
            for item in response_data:
                writer.writerow([item])

    elif isinstance(response_data, dict):
        # Dict response
        writer.writerow(["Key", "Value"])
        for key, value in response_data.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            writer.writerow([key, value])

    return output.getvalue().rstrip()


def format_csv(data: dict) -> str:
    """Format response as CSV.

    Args:
        data: Response dict from HardwareControlClient

    Returns:
        Comma-separated values string
    """
    if data.get("status") == "error":
        return f"Error,{data.get('message', 'Unknown error')}"

    response_data = data.get("data", [])

    output = io.StringIO()
    writer = csv.writer(output)

    if isinstance(response_data, list) and len(response_data) > 0:
        if isinstance(response_data[0], dict):
            # List of dicts
            keys = list(response_data[0].keys())
            writer.writerow(keys)
            for item in response_data:
                writer.writerow([item.get(k, "") for k in keys])
        else:
            # Simple list
            writer.writerow(["Item"])
            for item in response_data:
                writer.writerow([item])

    elif isinstance(response_data, dict):
        # Dict response
        writer.writerow(["Key", "Value"])
        for key, value in response_data.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            writer.writerow([key, value])

    return output.getvalue().rstrip()


def format_compact(data: dict) -> str:
    """Format response as compact single-line output.

    Args:
        data: Response dict from HardwareControlClient

    Returns:
        Compact string (e.g., "INSTRUMENT.PARAMETER=VALUE")
    """
    if data.get("status") == "error":
        return f"Error: {data.get('message', 'Unknown error')}"

    response_data = data.get("data", [])

    if isinstance(response_data, list) and len(response_data) > 0:
        if isinstance(response_data[0], dict):
            # List of dicts (get/set parameters)
            parts = []
            for item in response_data:
                if "instrument" in item and "parameter" in item:
                    inst = item["instrument"]
                    param = item["parameter"]
                    if "value" in item:
                        parts.append(f"{inst}.{param}={item['value']}")
                    elif "status" in item:
                        parts.append(f"{inst}.{param}:{item['status']}")
                    else:
                        parts.append(f"{inst}.{param}")
                else:
                    # Generic dict
                    kv_pairs = [f"{k}={v}" for k, v in item.items()]
                    parts.append(" ".join(kv_pairs))
            return " ".join(parts)
        else:
            # Simple list
            return " ".join(str(item) for item in response_data)

    elif isinstance(response_data, dict):
        # Dict response
        parts = []
        for key, value in response_data.items():
            if isinstance(value, list):
                value = ",".join(str(v) for v in value)
            parts.append(f"{key}={value}")
        return " ".join(parts)

    return str(response_data)
