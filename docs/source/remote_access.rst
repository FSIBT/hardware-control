Remote Access
=============

Hardware-control Apps can be queried and controlled remotely using IPC-based communication once remote access is turned on (see `Access Control`_). This enables:

* Command-line access via ``hc-query`` CLI tool
* LLM access via ``hc-mcp`` MCP server
* Programmatic access via Python client library

Overview
--------

When an App starts, it automatically:

1. Creates a ZMQ IPC socket for local communication
2. Registers itself in a platform-specific cache directory
3. Cleans up stale registry files from terminated processes

This registry-based discovery allows CLI tools and scripts to automatically find and connect to running Apps.

Registry System
---------------

Registry files are stored in:

* **Linux**: ``~/.cache/hardware-control/apps/``
* **macOS**: ``~/Library/Caches/hardware-control/apps/``
* **Windows**: ``C:\Users\<user>\AppData\Local\hardware-control\Cache\apps\``

Each running App creates a registry file (``app_<pid>.json``) containing:

.. code-block:: json

   {
     "app_name": "BeamLineControl",
     "pid": 12345,
     "ipc_address": "ipc:///tmp/hc_12345.sock",
     "birth_time": "2026-02-05T10:30:00.123456Z",
     "platform": "Darwin"
   }

Registry files are automatically cleaned up when the App exits or when stale files are detected.

Access Control
--------------

Remote access is **off** by default, so nothing can read from or control an
App until someone turns it on. There are three modes:

* **Off**: all requests are refused, including reads from ``hc-query``. The
  only exception is ``access_info``, which reports the mode.
* **Read-only**: reads and lists are allowed.
* **Full control**: settable parameters can be set and commands can be called.
  Pre-set and pre-call hooks still apply, so limits and interlocks should be
  implemented as hooks.

In an :class:`~hardware_control.base.HCMainWindow.HCMainWindow`, use the
*Remote Access* menu or click the indicator in the status bar. The indicator
appears if the program uses a status bar. The popup has these settings:

* **Keep after restart**: otherwise the App starts with access off again.
  Settings are saved per ``app_name``.
* **Time limit**: ``0`` for no limit, a number of minutes, or a time like
  ``2d8h4m``. Access goes back to off afterwards. A saved time limit keeps its
  end time, so a restart does not extend it.
* **Token**: if set, clients need to provide it. Use *Generate* to create a
  random one, and copy it right away, since only a hash is stored.

The same settings are available without a window:

.. code-block:: python

   app.set_remote_access("read-only", duration="8h", persist=True, token="...")

Clients read the token from the ``HC_TOKEN`` environment variable:

.. code-block:: bash

   export HC_TOKEN=<token>
   hc-query get PSU1.VOLTAGE

Mode changes, remote writes and commands, and refused tokens are logged. The
older ``get_instrument_parameter`` socket also follows the mode, and refuses
all requests if a token is set, since it cannot provide one.

.. warning::

   Access control does not protect against programs running under the same
   user account: an AI with file or shell access could read the token from its
   configuration or change the saved settings. To keep an AI limited to these
   modes, only give it the MCP tools, or run it as a different user or on a
   different computer.

Using the CLI Tool (hc-query)
------------------------------

The ``hc-query`` command-line tool provides access to running Apps.

List Running Apps
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   hc-query list

Example output:

.. code-block:: text

   ┏━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ App Name        ┃ Pid   ┃ Birth Time                   ┃
   ┡━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
   │ BeamLineControl │ 12345 │ 2026-02-05T10:30:00.123456Z  │
   └─────────────────┴───────┴──────────────────────────────┘

Get App Information
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   hc-query info --app BeamLineControl

Returns metadata about the App including uptime, instrument count, and instrument list.

Query Parameters
^^^^^^^^^^^^^^^^

Query single or multiple parameters:

.. code-block:: bash

   # Single parameter
   hc-query get PSU1.VOLTAGE

   # Multiple parameters
   hc-query get PSU1.VOLTAGE PSU2.CURRENT Scope.FREQUENCY

   # Specify App by name
   hc-query get PSU1.VOLTAGE --app BeamLineControl

   # Specify App by PID
   hc-query get PSU1.VOLTAGE --pid 12345

Set Parameters
^^^^^^^^^^^^^^

.. code-block:: bash

   # Single parameter
   hc-query set PSU1.VOLTAGE=42.5

   # Multiple parameters
   hc-query set PSU1.VOLTAGE=42.5 PSU2.CURRENT=1.2

   # Specify App
   hc-query set PSU1.VOLTAGE=42.5 --app BeamLineControl

Output Formats
^^^^^^^^^^^^^^

Use the ``--format`` option to control output formatting:

.. code-block:: bash

   # Table (default, human-readable)
   hc-query get PSU1.VOLTAGE --format table

   # JSON (for scripting)
   hc-query get PSU1.VOLTAGE --format json

   # Markdown table
   hc-query get PSU1.VOLTAGE --format markdown

   # CSV
   hc-query get PSU1.VOLTAGE --format csv

   # TSV (Google Sheets compatible)
   hc-query get PSU1.VOLTAGE --format sheets

   # Compact (single line: INSTRUMENT.PARAMETER=VALUE)
   hc-query get PSU1.VOLTAGE --format compact

Config Files
^^^^^^^^^^^^

Execute commands from a JSON config file:

.. code-block:: bash

   hc-query config commands.json

Config file format for querying:

.. code-block:: json

   {
     "command": "get_parameters",
     "queries": [
       {"instrument": "PSU1", "parameter": "VOLTAGE"},
       {"instrument": "PSU2", "parameter": "CURRENT"}
     ]
   }

Config file format for setting:

.. code-block:: json

   {
     "command": "set_parameters",
     "updates": [
       {"instrument": "PSU1", "parameter": "VOLTAGE", "value": "42.5"},
       {"instrument": "PSU2", "parameter": "CURRENT", "value": "1.2"}
     ]
   }

Using the MCP Server (hc-mcp)
------------------------------

The MCP (Model Context Protocol) server provides LLM access to hardware-control Apps.

Installation
^^^^^^^^^^^^

First install the optional MCP dependency:

.. code-block:: bash

   pip install -e ".[mcp]"

Starting the Server
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Auto-discover App (if only one running)
   hc-mcp

   # Specify App by name
   hc-mcp --app BeamLineControl

   # Specify App by PID
   hc-mcp --pid 12345

Claude Desktop Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add to your Claude Desktop config (``~/Library/Application Support/Claude/claude_desktop_config.json`` on macOS):

.. code-block:: json

   {
     "mcpServers": {
       "hardware-control": {
         "command": "hc-mcp",
         "args": ["--app", "BeamLineControl"],
         "env": {"HC_TOKEN": "<token, if the App requires one>"}
       }
     }
   }

Available MCP Tools
^^^^^^^^^^^^^^^^^^^

The MCP server exposes these tools to LLMs, depending on the access mode:

* **get_access_status**: Show the access mode (always available)
* **list_instruments**: List all instruments in the App (read-only and full)
* **list_parameters**: List parameters and commands of an instrument (read-only and full)
* **get_parameters**: Query parameter values (read-only and full)
* **set_parameters**: Set parameter values (full)
* **call_commands**: Call instrument commands (full)

The App checks every request, so changing the mode takes effect immediately,
even if an MCP client still shows an older list of tools.

Using the Python Client Library
--------------------------------

For custom integrations, use the Python client library:

.. code-block:: python

   from hardware_control.remote import HardwareControlClient, discover_app

   # Discover and connect to App
   app_info = discover_app(app_name="BeamLineControl")
   client = HardwareControlClient(
       ipc_address=app_info["ipc_address"],
       pid=app_info["pid"],
       app_name=app_info["app_name"]
   )

   # Query parameters
   response = client.get_parameters([
       {"instrument": "PSU1", "parameter": "VOLTAGE"},
       {"instrument": "PSU2", "parameter": "CURRENT"}
   ])
   print(response)

   # Set parameters
   response = client.set_parameters([
       {"instrument": "PSU1", "parameter": "VOLTAGE", "value": "42.5"}
   ])
   print(response)

   # List instruments
   response = client.list_instruments()
   print(response)

   # List parameters for an instrument
   response = client.list_parameters("PSU1")
   print(response)

   # Get App info
   response = client.get_app_info()
   print(response)

   # Clean up
   client.close()

Client API Reference
^^^^^^^^^^^^^^^^^^^^

.. autoclass:: hardware_control.remote.HardwareControlClient
   :members:
   :undoc-members:

Discovery Functions
^^^^^^^^^^^^^^^^^^^

.. automodule:: hardware_control.remote.discovery
   :members:
   :undoc-members:

Creating Apps with Remote Access
---------------------------------

Apps automatically support remote access. Just provide an ``app_name``:

.. code-block:: python

   from hardware_control.base import App

   # Create App with custom name
   app = App(app_name="BeamLineControl")

   # Add instruments as usual
   # ...

   # The App is now discoverable via hc-query and hc-mcp, but they can only
   # use it after remote access is turned on, see Access Control
   app.set_remote_access("read-only")

If you don't provide an ``app_name``, the App will use ``app_<pid>`` as the default name.

IPC Protocol
------------

The IPC protocol uses JSON over ZMQ REQ/REP sockets.

Request Format
^^^^^^^^^^^^^^

.. code-block:: text

   {
     "version": "1.0",
     "command": "get_parameters|set_parameters|call_commands|list_instruments|list_parameters|app_info|access_info",
     "token": "...",
     "queries": [...],
     "updates": [...],
     "commands": [...],
     "instrument": "..."
   }

Response Format
^^^^^^^^^^^^^^^

.. code-block:: text

   {
     "status": "success|error",
     "timestamp": "2026-02-05T10:30:15.123456Z",
     "app_name": "BeamLineControl",
     "message": "...",
     "data": [...]
   }

Available Commands
^^^^^^^^^^^^^^^^^^

* **get_parameters**: Query parameter values

  * Request: ``{"command": "get_parameters", "queries": [{"instrument": "PSU1", "parameter": "VOLTAGE"}]}``
  * Response: ``{"status": "success", "data": [{"instrument": "PSU1", "parameter": "VOLTAGE", "value": "42.5"}]}``

* **set_parameters**: Set parameter values

  * Request: ``{"command": "set_parameters", "updates": [{"instrument": "PSU1", "parameter": "VOLTAGE", "value": "50.0"}]}``
  * Response: ``{"status": "success", "data": [{"instrument": "PSU1", "parameter": "VOLTAGE", "status": "success"}]}``

* **call_commands**: Call instrument commands

  * Request: ``{"command": "call_commands", "commands": [{"instrument": "PSU1", "command": "RESET"}]}``
  * Response: ``{"status": "success", "data": [{"instrument": "PSU1", "command": "RESET", "status": "success"}]}``

* **access_info**: Get the access mode, the only request that works when access is off

  * Request: ``{"command": "access_info"}``
  * Response: ``{"status": "success", "data": {"access_mode": "off", "token_required": false, "token_valid": true}}``

* **list_instruments**: List all instruments

  * Request: ``{"command": "list_instruments"}``
  * Response: ``{"status": "success", "data": ["PSU1", "PSU2", "Scope"]}``

* **list_parameters**: List parameters for an instrument

  * Request: ``{"command": "list_parameters", "instrument": "PSU1"}``
  * Response: ``{"status": "success", "data": ["VOLTAGE", "CURRENT", "POWER"]}``

* **app_info**: Get App metadata

  * Request: ``{"command": "app_info"}``
  * Response: ``{"status": "success", "data": {"app_name": "BeamLineControl", "pid": 12345, "uptime_seconds": 3600, ...}}``

Error Handling
--------------

No Apps Running
^^^^^^^^^^^^^^^

.. code-block:: bash

   $ hc-query list
   No running hardware-control Apps found

Multiple Apps Without Specification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   $ hc-query get PSU1.VOLTAGE
   Error: Multiple Apps running. Specify one:
     BeamLineControl (pid: 12345)
     TestRig (pid: 12346)

   Use: hc-query --app <name> or --pid <pid>

App Crashed During Request
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "status": "error",
     "message": "App 'BeamLineControl' is no longer running"
   }

Invalid Parameter
^^^^^^^^^^^^^^^^^

The response will include an error field for the specific parameter query:

.. code-block:: json

   {
     "status": "success",
     "data": [
       {
         "instrument": "PSU1",
         "parameter": "INVALID",
         "error": "Cannot find parameter/command 'INVALID' for instrument 'PSU1'"
       }
     ]
   }

Platform Support
----------------

The remote access system works on:

* **Linux**: Full support (Unix domain sockets)
* **macOS**: Full support (Unix domain sockets)
* **Windows**: Full support (TCP on localhost)

Security Considerations
-----------------------

.. warning::

   The remote access system is designed for **local-only** access:

   * IPC sockets are local to the machine (not network-accessible)
   * Access is off by default, and an optional token can be required
   * If access is on without a token, anyone with local user access can
     use it, up to the current mode
   * On Windows the socket is a TCP port on localhost, so any local
     program can connect to it, so use a token

   :class:`~hardware_control.base.ZMQRemoteAdapter.ZMQSingleInstrument`
   is network-accessible and has no authentication either: anyone who can
   reach its address can control the instrument. Only use it on a trusted
   network.

   For remote access across networks, you would need to add:

   * Authentication/authorization mechanisms
   * Encrypted transport (e.g., SSH tunneling)
   * Rate limiting for set operations
   * Access control lists

Status of Set Requests
----------------------

Each entry in a ``set_parameters`` response has a ``status``:

* ``success``: the value was sent to the instrument. This does not confirm
  that the instrument applied it, so read the value back to check.
* ``deferred``: a hook, e.g. a ramp, will set the value later.
* ``skipped``: the App is running in dummy mode and nothing was set.
* ``error``: nothing was set and ``error`` gives the reason, e.g. an unknown
  or read-only parameter, an offline instrument, a value that contains
  whitespace, or a pre-set hook that rejected the value.

``hc-query`` exits with 1 if any entry has the status ``error``.

Dependencies
------------

Required Dependencies
^^^^^^^^^^^^^^^^^^^^^

* ``platformdirs >= 4.0.0`` - Cross-platform cache directory paths
* ``psutil >= 5.9.0`` - Process management
* ``pyzmq`` - ZMQ communication (already required by hardware-control)
* ``docopt`` - CLI parsing (already required)
* ``rich`` - Table formatting (already required)

Optional Dependencies
^^^^^^^^^^^^^^^^^^^^^

* ``mcp >= 2.3.0`` - Model Context Protocol server (for ``hc-mcp``)

Install optional dependencies with:

.. code-block:: bash

   pip install -e ".[mcp]"

Examples
--------

Example 1: Monitoring Power Supply Voltage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Query voltage every second and log to CSV
   while true; do
       hc-query get PSU1.VOLTAGE --format csv >> voltage_log.csv
       sleep 1
   done

Example 2: Batch Parameter Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a config file ``setup_beam.json``:

.. code-block:: json

   {
     "command": "set_parameters",
     "updates": [
       {"instrument": "PSU1", "parameter": "VOLTAGE", "value": "100.0"},
       {"instrument": "PSU2", "parameter": "VOLTAGE", "value": "50.0"},
       {"instrument": "FlowController", "parameter": "SETPOINT", "value": "2.5"}
     ]
   }

Execute:

.. code-block:: bash

   hc-query config setup_beam.json

Example 3: Python Monitoring Script
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from hardware_control.remote import HardwareControlClient, discover_app
   import time

   # Connect to App
   app_info = discover_app(app_name="BeamLineControl")
   client = HardwareControlClient(
       ipc_address=app_info["ipc_address"],
       pid=app_info["pid"]
   )

   # Monitor voltage and current
   try:
       while True:
           response = client.get_parameters([
               {"instrument": "PSU1", "parameter": "VOLTAGE"},
               {"instrument": "PSU1", "parameter": "CURRENT"}
           ])

           for item in response["data"]:
               print(f"{item['parameter']}: {item['value']}")

           time.sleep(1)
   except KeyboardInterrupt:
       print("Stopping...")
   finally:
       client.close()

Troubleshooting
---------------

Registry Files Not Cleaned Up
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If registry files accumulate from crashed Apps:

.. code-block:: python

   from hardware_control.remote import cleanup_stale_files

   cleaned = cleanup_stale_files()
   print(f"Cleaned up {len(cleaned)} stale registry files")

Or manually delete them:

.. code-block:: bash

   # macOS
   rm ~/Library/Caches/hardware-control/apps/app_*.json

   # Linux
   rm ~/.cache/hardware-control/apps/app_*.json

Connection Timeout
^^^^^^^^^^^^^^^^^^

If ``hc-query`` times out, the App may be unresponsive. Check:

1. Is the App Qt event loop running? (``app.exec()``)
2. Is the App frozen or blocked?
3. Check App logs for errors

Increase timeout in Python client:

.. code-block:: python

   client = HardwareControlClient(
       ipc_address=app_info["ipc_address"],
       pid=app_info["pid"],
       timeout=10000  # 10 seconds
   )
