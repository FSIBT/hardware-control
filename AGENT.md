## Project Overview

Hardware-control is a Python package for controlling laboratory equipment, developed to replace LabVIEW for instrument control at Lawrence Berkeley National Laboratory's Ion Beam Technology group. The package provides reusable GUI components for controlling various scientific instruments (power supplies, oscilloscopes, flow controllers, etc.) using PyQt6.

## Development Commands

### Testing
```bash
python -m pytest                    # Run all tests
python -m pytest tests/            # Run specific test directory
```

### Code Quality
```bash
ruff check                          # Run linting
ruff check --fix                   # Run linting with auto-fix
ruff format                        # Format code
pre-commit run --all-files         # Run all pre-commit hooks
```

### Examples and Demos
```bash
python examples/Single_Instrument_Demos/[demo_name].py --dummy --console --debug
# --dummy: Simulate instrument output without hardware
# --console: Redirect logging to terminal
# --debug: Enable debug logging level
```

### Build and Distribution
```bash
pip install -e .                   # Install in development mode
python -m build                    # Build distribution packages
```

## Architecture Overview

### Core Components

**Base Classes (`src/hardware_control/base/`)**:
- `App.py`: Main application class that manages instruments and provides the core event loop
- `Instrument.py`: Base class for all instrument drivers, handles connection protocols (pyvisa, socket, modbus)
- `ZMQAdapter.py`: Threading wrapper that enables ZMQ communication between instruments and main app
- `ZMQRemoteAdapter.py`: Enables remote instrument control across networks
- `Dataset.py`: Data collection and management
- `alarm.py` & `alarm_manager.py`: Alarm system for monitoring instrument states

**GUI Framework (`src/hardware_control/gui/`)**:
- `controls/`: Pre-built GUI controls for specific instrument types (power supplies, oscilloscopes, etc.)
- `widgets/`: Reusable UI components (plots, data displays, alarm widgets, scan widgets)

**Instrument Drivers (`src/hardware_control/instruments/`)**:
Organized by manufacturer (keysight/, rigol/, caen/, etc.), each containing specific instrument implementations that inherit from the base `Instrument` class.

### Communication Architecture

The system uses a threaded ZMQ (ZeroMQ) architecture:
- Each instrument runs in its own thread via `ZMQAdapter`
- Main app publishes commands to instruments via ZMQ
- Instruments publish status updates back to main app
- Remote instruments supported via `ZMQRemoteAdapter`
- Automatic reconnection and offline/online detection

### Hook System

Custom hook system in `base/hooks.py` allows pre/post-processing of instrument commands and parameter changes, enabling custom validation, logging, and data transformation.

## Key Development Patterns

### Adding New Instruments
1. Inherit from `Instrument` base class in `src/hardware_control/instruments/[manufacturer]/`
2. Implement `__init__()` with instrument_name and connection_address
3. Define parameters and commands using base class methods
4. Follow existing driver patterns (see `docs/source/adding_instruments.md`)

### GUI Development
- Use existing control templates from `gui/controls/` when possible
- GUI components should be instrument-agnostic and reusable
- Separate instrument logic from GUI logic (instruments have no Qt dependencies)

### Connection Management
- Instruments automatically handle online/offline states
- Support for multiple connection types: VISA, TCP sockets, Modbus, serial
- Dummy mode available for development without hardware

## Testing Strategy

- `pytest` for unit testing
- `--dummy` mode allows testing GUI layouts without physical instruments
- Test coverage focuses on instrument communication and data handling
- Hardware-dependent tests require actual instrument connections

## Code Style

- Uses `ruff` for linting and formatting (configured in `pyproject.toml`)
- Pre-commit hooks enforce code quality
- Line length: 88 characters
- Double quotes for strings
- No manual code formatting needed - handled by pre-commit hooks

## Git Workflow

### Staging Files
- **NEVER use `git add .` or `git add -A`** - these can accidentally stage untracked files
- **ALWAYS explicitly list files to stage**: `git add src/file1.py src/file2.py`
- Check `git status` before committing to verify only intended files are staged

### Commit Messages
- **Single line commits only** - keep messages concise and descriptive
- **Use component prefixes for categorization**:
  - `CI:` for CI/build system changes
  - `App:` for main application changes
  - `picoscope:` for picoscope-related changes
  - Component names (e.g., `Dataset:`, `ZMQ:`, `Instrument:`) for specific modules
  - No prefix for general changes
- **Examples of good commit messages**:
  - `CI: Fix Bitbucket CI configuration for PyQt6 headless testing`
  - `Fix datetime arithmetic type errors in Dataset and scan widget`
  - `Apply error handling framework to core operations`
