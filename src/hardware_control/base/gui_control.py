"""Base class for hardware control GUI elements with parameter validation.

This module provides the ValidatedControl mixin class that automatically validates
that instruments provide all required parameters and commands. Required parameters
are specified as class attributes, making them visible to both runtime validation
and Sphinx documentation generation.
"""

import logging


logger = logging.getLogger(__name__)


def document_required_parameters(cls):
    """Class decorator that adds parameter documentation to GUI control docstrings.

    This decorator formats the _required_parameters, _required_read_only,
    _required_write_only, and _required_commands class attributes into a readable
    documentation block that appears in Sphinx-generated documentation.

    The decorator is applied automatically to all ValidatedControl subclasses,
    but can also be applied explicitly for better IDE support.

    Parameters
    ----------
    cls : class
        The GUI control class to document

    Returns
    -------
    class
        The same class with updated docstring

    Example
    -------
    .. code-block:: python

        @document_required_parameters
        class MyControl(ValidatedControl, QGroupBox):
            _required_parameters = ["VOLTAGE", "CURRENT"]
            _required_commands = ["RESET"]

            def __init__(self, app, instrument_name, ...):
                super().__init__(app, instrument_name, ...)
                # Validation happens automatically in super().__init__
    """
    # Get parameters from class attributes
    params_rw = getattr(cls, "_required_parameters", [])
    params_read = getattr(cls, "_required_read_only", [])
    params_write = getattr(cls, "_required_write_only", [])
    cmds = getattr(cls, "_required_commands", [])

    # Build required_params dict for formatting
    required_params = {}
    for p in params_rw:
        required_params[p] = {"type": "parameter", "access": "read_write"}
    for p in params_read:
        required_params[p] = {"type": "parameter", "access": "read"}
    for p in params_write:
        required_params[p] = {"type": "parameter", "access": "write"}
    for c in cmds:
        required_params[c] = {"type": "command"}

    if required_params:
        _append_params_to_class_docs(cls, required_params)

    return cls


def _append_params_to_class_docs(cls, required_params):
    """Append required parameters documentation to class docstring.

    Parameters
    ----------
    cls : class
        The class to modify
    required_params : dict
        Dictionary of parameter specifications
    """
    if not required_params:
        return

    # Group by type
    params_read = []
    params_write = []
    params_rw = []
    cmds = []

    for name, spec in sorted(required_params.items()):
        if spec["type"] == "command":
            cmds.append(name)
        else:
            access = spec.get("access", "read_write")
            if access == "read":
                params_read.append(name)
            elif access == "write":
                params_write.append(name)
            else:
                params_rw.append(name)

    # Build documentation table
    lines = ["\n\n**Required Instrument Parameters**\n"]

    if params_rw:
        lines.append("\nRead/Write Parameters:\n")
        for p in params_rw:
            lines.append(f"  - ``{p}``\n")

    if params_read:
        lines.append("\nRead-only Parameters:\n")
        for p in params_read:
            lines.append(f"  - ``{p}``\n")

    if params_write:
        lines.append("\nWrite-only Parameters:\n")
        for p in params_write:
            lines.append(f"  - ``{p}``\n")

    if cmds:
        lines.append("\nCommands:\n")
        for c in cmds:
            lines.append(f"  - ``{c}``\n")

    # Append to class docstring
    doc_addition = "".join(lines)
    if cls.__doc__:
        cls.__doc__ += doc_addition
    else:
        cls.__doc__ = doc_addition


class ValidatedControl:
    """Mixin for controls that validate instrument parameters.

    This mixin automatically validates that instruments provide all required
    parameters and commands. Required parameters are specified as class attributes:

    - ``_required_parameters``: Read/write parameters
    - ``_required_read_only``: Read-only parameters
    - ``_required_write_only``: Write-only parameters
    - ``_required_commands``: Commands

    Validation happens automatically in __init__ when the control is instantiated.
    No manual validation call is needed.

    Example
    -------
    .. code-block:: python

        from hardware_control.base.gui_control import (
            ValidatedControl,
            document_required_parameters,
        )


        @document_required_parameters
        class MyControl(ValidatedControl, QGroupBox):
            # Specify required parameters as class attributes
            _required_parameters = ["VOLTAGE", "CURRENT"]
            _required_read_only = ["STATUS"]
            _required_commands = ["RESET"]

            def __init__(self, app, instrument_name, widget_name="My Control"):
                # Validation happens automatically here
                super().__init__(app, instrument_name, widget_name)

                self.app = app
                self.instrument = instrument_name

                # Create widgets
                self.voltage = HCLabel(app, instrument_name, "VOLTAGE", ...)
                # ... widgets can be created without manual registration

    Parameters
    ----------
    app : App
        The hardware control application instance
    instrument_name : str
        Name of the instrument this control interfaces with
    *args, **kwargs
        Passed to parent class (typically QWidget)

    Attributes
    ----------
    app : App
        Reference to the app instance
    instrument : str
        Reference to the instrument name
    """

    def __init_subclass__(cls):
        """Automatically apply documentation decorator to all subclasses."""
        super().__init_subclass__()
        document_required_parameters(cls)

    def __init__(self, app, instrument_name: str, *args, **kwargs):
        """Initialize and validate control.

        Parameters
        ----------
        app : App
            The hardware control application instance
        instrument_name : str
            Name of the instrument this control interfaces with
        *args, **kwargs
            Passed to parent class
        """
        self.app = app
        self.instrument = instrument_name

        # Collect required parameters from instance or class attributes
        # Instance attributes take precedence (allows dynamic parameter lists)
        required_params = {}

        # Read/write parameters
        for param in getattr(self, "_required_parameters", []):
            required_params[param] = {"type": "parameter", "access": "read_write"}

        # Read-only parameters
        for param in getattr(self, "_required_read_only", []):
            required_params[param] = {"type": "parameter", "access": "read"}

        # Write-only parameters
        for param in getattr(self, "_required_write_only", []):
            required_params[param] = {"type": "parameter", "access": "write"}

        # Commands
        for cmd in getattr(self, "_required_commands", []):
            required_params[cmd] = {"type": "command"}

        # Validate if there are any requirements
        if required_params:
            self._validate_parameters(required_params)

        # Pass remaining args to next class in MRO (typically QGroupBox/QWidget)
        super().__init__(*args, **kwargs)

    def _validate_parameters(self, required_params: dict) -> None:
        """Validate that instrument provides all required parameters.

        Parameters
        ----------
        required_params : dict
            Dictionary mapping parameter names to their specifications

        Raises
        ------
        ValueError
            If instrument is missing required parameters/commands. The error message
            will clearly list what's missing.
        """
        # Check if instrument exists in the app
        if self.instrument not in self.app.instruments:
            raise ValueError(
                f"Instrument '{self.instrument}' not found in app. "
                f"Make sure the instrument is added to the app before creating the GUI control.\n"
                f"Available instruments: {list(self.app.instruments)}"
            )

        # Get instrument capabilities
        read_params, set_params, commands = (
            self.app.get_instrument_parameters_and_commands(self.instrument)
        )

        # Check each required parameter
        missing = []
        for param_name, spec in required_params.items():
            param_type = spec["type"]
            access = spec.get("access", "read_write")

            if param_type == "command":
                if param_name not in commands:
                    missing.append(f"{param_name} (command)")
            elif param_type == "parameter":
                if access in ("read", "read_write") and param_name not in read_params:
                    missing.append(f"{param_name} (readable)")
                if access in ("write", "read_write") and param_name not in set_params:
                    missing.append(f"{param_name} (writable)")

        if missing:
            raise ValueError(
                f"Instrument '{self.instrument}' missing required parameters/commands "
                f"for {self.__class__.__name__}:\n  - "
                + "\n  - ".join(missing)
                + f"\n\nRequired: {list(required_params.keys())}"
            )

        logger.info(
            f"{self.__class__.__name__} validated successfully "
            f"({len(required_params)} parameters/commands)"
        )
