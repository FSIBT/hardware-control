# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

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
