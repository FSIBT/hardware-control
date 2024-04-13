# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

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

### CHANGED
- changed to src/ layout
- move setup.{cfg,py} into pyproject.toml
- require python >= 3.9 (minimum version for numpy)
- updated pre-commit versions and run on all files
- updated pipelines and readthedocs python versions
- MWController: changed order of widgets
- MultiPowerSupply: better on/off buttons, better status icons

## [3.0.1] 2023-02-18

### CHANGED
- updated docs
- Removed auto_update from HCPushButton since it connects to a command not a parameter

### FIXED
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
