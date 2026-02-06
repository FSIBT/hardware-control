"""Client library for communicating with hardware-control Apps via IPC."""

import json

import zmq

from .discovery import is_app_alive


class HardwareControlClient:
    """Client for communicating with a hardware-control App via ZMQ IPC.

    Example:
        >>> from hardware_control.remote import HardwareControlClient, discover_app
        >>> app_info = discover_app(app_name="BeamLineControl")
        >>> client = HardwareControlClient(
        ...     ipc_address=app_info["ipc_address"], pid=app_info["pid"]
        ... )
        >>> result = client.get_parameters([{"instrument": "PSU1", "parameter": "VOLTAGE"}])
        >>> client.close()
    """

    def __init__(
        self, ipc_address: str, pid: int, timeout: int = 5000, app_name: str = ""
    ):
        """Initialize client connection to App.

        Args:
            ipc_address: ZMQ IPC address (e.g., "ipc:///tmp/hc_12345.sock")
            pid: Process ID of the App
            timeout: Timeout in milliseconds for send/receive operations
            app_name: Name of the App (for error messages)
        """
        self.ipc_address = ipc_address
        self.pid = pid
        self.timeout = timeout
        self.app_name = app_name or f"app_{pid}"

        # Create ZMQ context and REQ socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, timeout)
        self.socket.setsockopt(zmq.SNDTIMEO, timeout)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(ipc_address)

    def is_alive(self) -> bool:
        """Check if the App process is still running.

        Returns:
            True if App process exists, False otherwise
        """
        return is_app_alive(self.pid)

    def _send_request(self, request: dict) -> dict:
        """Send a request to the App and receive response.

        Args:
            request: Request dictionary with version and command

        Returns:
            Response dictionary

        Raises:
            RuntimeError: If App is not alive, communication fails, or timeout occurs
        """
        if not self.is_alive():
            raise RuntimeError(
                f"App '{self.app_name}' (pid: {self.pid}) is no longer running"
            )

        try:
            # Send request
            request_json = json.dumps(request)
            self.socket.send_string(request_json)

            # Receive response
            response_json = self.socket.recv_string()
            response = json.loads(response_json)

            return response

        except zmq.error.Again:
            raise RuntimeError(
                f"Timeout waiting for response from App '{self.app_name}' "
                f"after {self.timeout}ms"
            )
        except zmq.error.ZMQError as e:
            raise RuntimeError(
                f"ZMQ communication error with App '{self.app_name}': {e}"
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from App '{self.app_name}': {e}")

    def get_parameters(self, queries: list[dict]) -> dict:
        """Query multiple parameters from instruments.

        Args:
            queries: List of dicts with keys: instrument, parameter
                    Example: [{"instrument": "PSU1", "parameter": "VOLTAGE"}]

        Returns:
            Response dict with status, timestamp, app_name, and data array

        Example:
            >>> client.get_parameters(
            ...     [
            ...         {"instrument": "PSU1", "parameter": "VOLTAGE"},
            ...         {"instrument": "PSU2", "parameter": "CURRENT"},
            ...     ]
            ... )
            {
                "status": "success",
                "timestamp": "2026-02-05T10:30:15.123456Z",
                "app_name": "BeamLineControl",
                "data": [
                    {"instrument": "PSU1", "parameter": "VOLTAGE", "value": 42.5},
                    {"instrument": "PSU2", "parameter": "CURRENT", "value": 1.2}
                ]
            }
        """
        request = {"version": "1.0", "command": "get_parameters", "queries": queries}
        return self._send_request(request)

    def set_parameters(self, updates: list[dict]) -> dict:
        """Set multiple parameters on instruments.

        Args:
            updates: List of dicts with keys: instrument, parameter, value
                    Example: [{"instrument": "PSU1", "parameter": "VOLTAGE", "value": 42.5}]

        Returns:
            Response dict with status, timestamp, app_name, and data array

        Example:
            >>> client.set_parameters(
            ...     [{"instrument": "PSU1", "parameter": "VOLTAGE", "value": 42.5}]
            ... )
            {
                "status": "success",
                "timestamp": "2026-02-05T10:30:15.123456Z",
                "app_name": "BeamLineControl",
                "data": [
                    {"instrument": "PSU1", "parameter": "VOLTAGE", "status": "success"}
                ]
            }
        """
        request = {"version": "1.0", "command": "set_parameters", "updates": updates}
        return self._send_request(request)

    def list_instruments(self) -> dict:
        """Get list of all instruments in the App.

        Returns:
            Response dict with status, timestamp, app_name, and data array

        Example:
            >>> client.list_instruments()
            {
                "status": "success",
                "timestamp": "2026-02-05T10:30:15.123456Z",
                "app_name": "BeamLineControl",
                "data": ["PSU1", "PSU2", "Oscilloscope"]
            }
        """
        request = {"version": "1.0", "command": "list_instruments"}
        return self._send_request(request)

    def list_parameters(self, instrument: str) -> dict:
        """Get list of all parameters for a specific instrument.

        Args:
            instrument: Name of the instrument

        Returns:
            Response dict with status, timestamp, app_name, and data array

        Example:
            >>> client.list_parameters("PSU1")
            {
                "status": "success",
                "timestamp": "2026-02-05T10:30:15.123456Z",
                "app_name": "BeamLineControl",
                "data": ["VOLTAGE", "CURRENT", "POWER", "ENABLE"]
            }
        """
        request = {
            "version": "1.0",
            "command": "list_parameters",
            "instrument": instrument,
        }
        return self._send_request(request)

    def get_app_info(self) -> dict:
        """Get metadata about the App.

        Returns:
            Response dict with status, timestamp, and data dict containing:
            - app_name: Name of the App
            - pid: Process ID
            - birth_time: When the App started (ISO format)
            - uptime_seconds: How long the App has been running
            - instrument_count: Number of instruments
            - instruments: List of instrument names

        Example:
            >>> client.get_app_info()
            {
                "status": "success",
                "timestamp": "2026-02-05T10:30:15.123456Z",
                "app_name": "BeamLineControl",
                "data": {
                    "app_name": "BeamLineControl",
                    "pid": 12345,
                    "birth_time": "2026-02-05T10:00:00.000000Z",
                    "uptime_seconds": 1815.123,
                    "instrument_count": 3,
                    "instruments": ["PSU1", "PSU2", "Oscilloscope"]
                }
            }
        """
        request = {"version": "1.0", "command": "app_info"}
        return self._send_request(request)

    def close(self):
        """Clean up resources and close connection."""
        if hasattr(self, "socket"):
            self.socket.close()
        if hasattr(self, "context"):
            self.context.term()
