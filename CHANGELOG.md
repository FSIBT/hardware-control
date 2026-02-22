# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added
- Remote access system for querying and controlling Apps
  - Registry-based App discovery in platform-specific cache directories
  - IPC-based communication via ZMQ REQ/REP sockets
  - `hc-query` CLI tool for querying/setting parameters with multiple output formats (table, json, markdown, csv, compact)
  - `hc-mcp` MCP server for LLM access to hardware-control Apps
  - Python client library (`hardware_control.remote.HardwareControlClient`) for custom integrations
  - `App` now accepts optional `app_name` parameter for custom naming
  - New dependencies: `platformdirs >= 4.0.0`, `psutil >= 5.9.0`
  - Optional dependency: `mcp >= 0.9.0` for MCP server support

### Changed
  - switched from docopt to docopt-ng

## [4.0.0] 2026-01-07

### Added
- use setproctitle for better names of the subprocesses
- Virtual instruments: support for non-hardware data sources (web APIs, calculations, user input)
  - `App.add_virtual_instrument()` to create virtual instruments
  - `App.update_virtual_instrument_parameter()` to update values
  - Full integration with widgets, datasets, alarms, and hooks
  - New example: `examples/virtual_instrument.py`
- ONLINE parameter hooks: track instrument connection events
  - Every instrument has a special `ONLINE` parameter
  - Attach `post_read_hooks` to trigger actions when instruments connect/disconnect
  - New example: `examples/online_hook.py` demonstrating connection event tracking
- Type hints added throughout base directory for better IDE support
- Python 3.14 support in tests and pyproject.toml
- Plotting data sets: separate autoscaling for X and Y
- Plotting data sets: Ability to select data to be plotted within a dataset
- New Vortran Laser driver
- New Spellman High Voltage Power Supply driver
- Adam6024: added readout of digital channels
- Cean RSeries: added ability to set ramp up/down speed
- Ability to change the logfile location using a environement variable
- New AlarmManager class to trigger alarms (currently only audio alarms)

### Fixed
- Dataset: header column order now matches data order
- Dataset: auto update of instrument parameters when parameter=None
- App: message parsing now continues processing all instruments after errors
- HCMainWindow: use sys.exit() instead of exit() for proper cleanup
- ZMQRemoteAdapter: removed debug print statement
- Alarms: fixed typo in variable name (duration_s → duration)
- Various typos in comments and docstrings
- Replaced pkg_resources with importlib
- CAEN power supply: Setting max current and reading out max voltage
- pytest warning

### Changed
- **Breaking**: Instrument connection API refactored to prevent resource leaks
  - `try_connect()` now uses template method pattern (do not override)
  - Override `establish_connection()` for custom device creation
  - Override `cleanup_connection()` for custom cleanup logic
  - Override `on_connect()` for post-connection initialization
  - Deprecation warnings added for old API (backward compatible for now)
  - Migrated 6 built-in drivers: Stradus, AdamBase, Ni_9000, Picoscope, SRS_DG535, TPI
- Instrument: `add_parameter()` now validates at least one command is provided
- ZMQAdapter: magic numbers moved to class constants (CONNECTION_CHECK_INTERVAL, POLL_TIMEOUT_MS)
- require python3.11 (minimum supported numpy version)
- switch to ruff (from black and pyupgrade)
- updated how the license is specified in pyproject.toml (PEP 639)
- updated docs

## [3.1.0] 2024-04-13

### Fixed
- automatic update in App.py of instrument parameters was not working correctly
- Keysight 3600 power supply UI: remove on/off buttons for E3631A mode (only global on/off available)
- Adam6015: detect offline mode in case command times out
- plotbase: define variables in init
- Picoscope: setting larger voltage ranges
- MWController: added display of actual power level
- TPI: by default show -9 to +9 dBm, option to override this
- TPI: fix use in dummy mode

### Added
- Keysight 3600 power supply: add readout of persona
- Picoscope: readout of scope parameters
- Add ZMQ channel to allow other programs to request instrument parameters

### Changed
- changed to src/ layout
- move setup.{cfg,py} into pyproject.toml
- require python >= 3.9 (minimum version for numpy)
- updated pre-commit versions and run on all files
- updated pipelines and readthedocs python versions
- MWController: changed order of widgets
- MultiPowerSupply: better on/off buttons, better status icons

## [3.0.1] 2023-02-18

### Changed
- updated docs
- Removed auto_update from HCPushButton since it connects to a command not a parameter

### Fixed
- HCLabel: force convertion to string, so that call to .rjust works all the time
- TPI: several fixes
- Fix quering for a serial device

## [3.0.0] 2023-02-18

The main new feature is updating to pyqt6.

### Changed
- Update from PyQt5 to PyQt6
- Update to pymodbus > 3.0.0
- Update to nidaqmx >= 0.6.4
- Update qtconsole >= 5.3.2
- any parameter used in a HC-widget or dataset will now by default be updated in app

### Fixed
- fixed button click in MultiPowerSupply
- fixed removing continuous command from Oscilloscope
- fixed setting value in HCSpinBox
- fixed try_reconnect for DG5353
- fixed autoscale in plot widget

### Added
- TPI: new microwave controller
- Lakeshore 372: new instrument driver
- Keithley 2400: add voltage measurements
- Keithley 2001: new driver
- SRS CIS200: add clear offset command
- SRS DG645: new driver
- CAEN: new function to read out v_max

### Removed
- GPy dependencies

## [2.2.0] 2022-07-26

### Added
- New very basic driver for HP 3478A and HP 33401A

### Changed
- Ability to pick pyvisa backend when creating an instrument

## [2.1.1] 2022-04-14

### Fixed
- Author list in setup.cfg cannot be multiline

## [2.1.0] 2022-04-13

### Added
- We already have an option to automatically update a list of
  parameteres, add the same for commands that should be called
  periodically
- Created the TracePlotter widget for plotting traces or any data not
  saved as a dataset. TracePlotter 'intercepts' data as it is coming
  from the instrument (via a hook) rather than reading it from the App
  data dictionary
- Hook for splitting a string
- Siglent Function Generator enable button
- Better support of Ctrl-C to stop the app

### Changed
- Hooks can now return non-string values
- Ability to skip certain datasets in PlotTool
- Examples now take a connection address on the command line, to make
  it easier to run them with real hardware
- Keysight 36300: convert current and voltage to floats
- VQM835: add option to read and set calibration constant
- Picoscope: update driver, add support fro 2000-series

### Fixed
- Fix Siglent Function Generator impedance and waveform inputs
- Fix return value for hook used with oscilloscopes

## [2.0.0] 2021-11-24

### Changed
- Complete rewrite on how the instruments threads communicate with the main app. This used to rely on internal Qt slots and signals and is now being replaced by ZMQ-based communication.
- Complete rewrite on where and how instrument data is stored. Instead of storing it at the instrument level, we now store it in app._data. This enables us to completely separate the UI from the instruments.
- Complete rewrite on how instrument parameters are handled. Instead of a large if statement where different parameters/commands are checked for, we now use an add_command/add_parameter function that defines either a python function to be called or ascii strings that are sent to the instrument.
- Updated the documentation
- scan widget: use python function directly instead of macros
- MacroRunnerTool now uses python function directly, renamed to FunctionRunnerTool

### Added
- Added Gaussian Process functionality during scanning to figure out where to scan next (instead of
using linear scans)

### Removed
- Removed old functionality that is not used anymore, e.g., MeasurementDirector, MeasurementRequests, macros

## [1.0.0] 2020-09-09

Started to use the program at our test stands. Lots of cleanup and improvements

### Changed
- Changed directory structure to separate backend and gui classes and make import easier
- Renamed LoggerTool to DataWidget
- pylint/pyflake cleanup
- Changed all settings and values keys to upper case

### Added
- Gui/base/logging: some function to easily setup different logging styles
- Documentation on [RTD](https://hardware-control.readthedocs.io/en/latest/index.html)
- General hooks when setting variables and getting values from backends
- Simplify import by importing items in __init__.py of the subpackages
  and moving some variables into classes
- This changelog file

### Removed
- Removed app.variables
- Removed old, unused code
- Clean up examples

## [0.0.2] 2020-07-08

### Added
- first release on pypi
