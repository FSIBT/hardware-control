"""Base class for hardware control GUI elements with parameter validation.

This module provides the ValidatedControl mixin class that automatically validates
that instruments provide all required parameters and commands before the GUI control
is used. It also auto-generates documentation of required parameters.
"""

import logging


logger = logging.getLogger(__name__)


class ValidatedControl:
    """Mixin for controls that validate instrument parameters.

    This mixin automatically handles parameter collection and provides validation.
    Controls must pass 'app' and 'instrument_name' as first two positional arguments
    to super().__init__().

    The validation system works in three steps:
    1. HC widgets (HCLabel, HCLineEdit, etc.) automatically register their parameters
    2. Control manually adds any parameters it uses directly (not through widgets)
    3. Control calls _validate_parameters() after all widgets are created

    Example
    -------
    .. code-block:: python

        from hardware_control.base.gui_control import ValidatedControl


        class MyControl(ValidatedControl, QGroupBox):
            def __init__(self, app, instrument_name, widget_name="My Control"):
                # Auto-starts parameter collection
                super().__init__(app, instrument_name, widget_name)

                self.app = app
                self.instrument = instrument_name

                # Create widgets (they auto-register)
                self.voltage = HCLabel(app, instrument_name, "VOLTAGE", ...)

                # Manually add parameters used directly
                self._add_required_parameter("RESET", param_type="command")

                # IMPORTANT: Must call this after creating all widgets!
                self._validate_parameters()

    Parameters
    ----------
    app : App
        The hardware control application instance
    instrument_name : str
        Name of the instrument this control interfaces with
    *args, **kwargs
        Passed to parent class

    Attributes
    ----------
    app : App
        Reference to the app instance for validation
    instrument : str
        Reference to the instrument name for validation
    _required_params : dict
        Dictionary of required parameters/commands
    _validated : bool
        Flag indicating whether validation has been performed
    """

    def __init__(self, app, instrument_name: str, *args, **kwargs):
        """Initialize validation system.

        Automatically starts parameter collection. HC widgets created after this
        will register their parameters automatically.

        Parameters
        ----------
        app : App
            The hardware control application instance
        instrument_name : str
            Name of the instrument this control interfaces with
        *args, **kwargs
            Passed to parent class
        """
        # Start parameter collection automatically
        self.app = app
        self.instrument = instrument_name
        self._required_params = {}
        self._validated = False

        # Provide registration function to app
        # This will be called by HC widgets when they are created
        def register(
            inst: str,
            param: str,
            param_type: str = "parameter",
            access: str = "read_write",
        ):
            """Register a parameter requirement from a widget.

            Parameters
            ----------
            inst : str
                Instrument name
            param : str
                Parameter or command name
            param_type : str
                'parameter' or 'command'
            access : str
                'read', 'write', or 'read_write' (only for param_type='parameter')
            """
            if inst == instrument_name:
                self._required_params[param] = {"type": param_type, "access": access}

        app._register_widget_parameter = register

        # Pass remaining args to next class in MRO (typically QGroupBox)
        super().__init__(*args, **kwargs)

    def _add_required_parameter(
        self, parameter: str, param_type: str = "parameter", access: str = "read_write"
    ) -> None:
        """Manually add a required parameter not used through a widget.

        Use this for parameters you access directly via app.get_instrument_parameter(),
        app.set_instrument_parameter(), or app.call_instrument_command().

        Parameters you access through HC widgets (HCLabel, HCLineEdit, etc.) are
        automatically registered and do not need to be added manually.

        Parameters
        ----------
        parameter : str
            Parameter or command name
        param_type : str, optional
            'parameter' or 'command', by default 'parameter'
        access : str, optional
            'read', 'write', or 'read_write' (only for param_type='parameter'),
            by default 'read_write'

        Example
        -------
        .. code-block:: python

            # For a command you call directly
            self._add_required_parameter("RESET", param_type="command")

            # For a parameter you read directly
            self._add_required_parameter("STATUS", access="read")

            # For a parameter you write directly
            self._add_required_parameter("MODE", access="write")
        """
        self._required_params[parameter] = {"type": param_type, "access": access}

    def _validate_parameters(self) -> None:
        """Validate that instrument provides all required parameters.

        This method MUST be called after creating all widgets and adding manual
        parameters. It performs validation and auto-generates documentation.

        Raises
        ------
        ValueError
            If instrument is missing required parameters/commands. The error message
            will clearly list what's missing.

        Example
        -------
        .. code-block:: python

            def __init__(self, app, instrument_name, ...):
                super().__init__(app, instrument_name, ...)

                # Create all widgets
                self.voltage = HCLabel(...)

                # Add manual parameters
                self._add_required_parameter("RESET", param_type='command')

                # IMPORTANT: Validate everything
                self._validate_parameters()
        """
        if self._validated:
            return  # Already validated

        # Clean up app registration
        if hasattr(self.app, "_register_widget_parameter"):
            delattr(self.app, "_register_widget_parameter")

        if not self._required_params:
            self._validated = True
            logger.debug(
                f"{self.__class__.__name__} has no required parameters to validate"
            )
            return  # No validation needed

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
        for param_name, spec in self._required_params.items():
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
                + f"\n\nRequired: {list(self._required_params.keys())}"
            )

        # Auto-generate documentation of required parameters
        self._append_required_params_to_docs()
        self._validated = True

        logger.info(
            f"{self.__class__.__name__} validated successfully "
            f"({len(self._required_params)} parameters/commands)"
        )

    def _append_required_params_to_docs(self) -> None:
        """Automatically append required parameters table to class docstring.

        This generates a formatted list of required parameters that appears in
        the Sphinx-generated documentation. The list is organized by parameter type
        and access pattern.
        """
        if not self._required_params:
            return

        # Group by type
        params_read = []
        params_write = []
        params_rw = []
        cmds = []

        for name, spec in sorted(self._required_params.items()):
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
        if self.__class__.__doc__:
            self.__class__.__doc__ += doc_addition
        else:
            self.__class__.__doc__ = doc_addition
