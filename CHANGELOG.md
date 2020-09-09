# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

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
