# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Changed
- changed directory structure to separate backend and gui classes and make import easier
- Renamed LoggerTool to DataWidget
- pylint/pyflake cleanup

### Added
- gui/base/logging: some function to easily setup different logging styles
- documentation on [RTD](https://hardware-control.readthedocs.io/en/latest/index.html)
- general hooks when setting variables and getting values from backends
- simplify import by importing items in __init__.py of the subpackages
  and moving some variables into classes
- this changelog file

### Removed
- Removed app.variables
- Removed old, unused code

## [0.0.2] 2020-07-08
### Added
- first release on pypi
