Creating GUI Controls
=====================

This guide shows how to create custom GUI controls with automatic parameter validation.

Parameter Validation Pattern
-----------------------------

Hardware Control provides automatic validation to ensure instruments support all parameters
used by your GUI control. This prevents runtime errors when a parameter doesn't exist.

How It Works
~~~~~~~~~~~~

1. **Declare required parameters as class attributes**: Use ``_required_parameters``, ``_required_read_only``, ``_required_write_only``, and ``_required_commands``
2. **Inherit from ValidatedControl**: Use it as first parent class
3. **Pass app and instrument_name to super().__init__()**: Validation happens automatically
4. **Documentation is auto-generated**: Sphinx sees the required parameters at import time

That's it! No manual validation calls, no parameter registration - just declare what you need.

Example: Simple Control
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
    from hardware_control.base.gui_control import ValidatedControl
    from ..widgets import HCLabel, HCLineEdit

    class SimpleVoltmeter(ValidatedControl, QGroupBox):
        """A simple voltmeter control."""

        # Declare required parameters as class attributes
        _required_parameters = ["RANGE"]  # Read/write
        _required_read_only = ["VOLTAGE"]  # Read-only
        _required_commands = ["AUTO_RANGE"]  # Commands

        def __init__(self, app, instrument_name: str, widget_name: str = "Voltmeter"):
            # Validation happens automatically in super().__init__()
            super().__init__(app, instrument_name, widget_name)

            self.app = app
            self.instrument = instrument_name

            # Create widgets - no registration needed!
            self.voltage_display = HCLabel(
                app, instrument_name, "VOLTAGE",
                label="Voltage", unit="V"
            )

            self.range_selector = HCLineEdit(
                app, instrument_name, "RANGE",
                label="Range"
            )

            # Build layout
            layout = QVBoxLayout()
            layout.addWidget(self.voltage_display.label)
            layout.addWidget(self.voltage_display)
            layout.addWidget(self.range_selector.label)
            layout.addWidget(self.range_selector)
            self.setLayout(layout)

Required Parameter Attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Declare required parameters as class attributes:

**_required_parameters** (list of str):
   Parameters that the control both reads and writes.

   .. code-block:: python

      _required_parameters = ["VOLTAGE", "CURRENT", "RANGE"]

**_required_read_only** (list of str):
   Parameters that the control only reads (displays, uses for calculations, etc.).

   .. code-block:: python

      _required_read_only = ["STATUS", "ERROR_CODE"]

**_required_write_only** (list of str):
   Parameters that the control only sets (rare, but supported).

   .. code-block:: python

      _required_write_only = ["CALIBRATION_MODE"]

**_required_commands** (list of str):
   Commands that the control calls (operations without return values).

   .. code-block:: python

      _required_commands = ["RESET", "AUTO_RANGE", "CLEAR_ERRORS"]

Error Messages
~~~~~~~~~~~~~~

If validation fails during ``super().__init__()``, you get a clear error message:

.. code-block:: text

    ValueError: Instrument 'DMM_1' missing required parameters/commands for SimpleVoltmeter:
      - AUTO_RANGE (command)
      - VOLTAGE (readable)

    Required: ['VOLTAGE', 'RANGE', 'AUTO_RANGE']

This tells you exactly what's missing and helps debug instrument compatibility issues.

Auto-Generated Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Required parameters are automatically documented in Sphinx! Your class docstring will be
augmented with a "Required Instrument Parameters" section:

.. code-block:: python

    class SimpleVoltmeter(ValidatedControl, QGroupBox):
        """
        A simple voltmeter control.

        **Required Instrument Parameters**

        Read/Write Parameters:
          - ``RANGE``

        Read-only Parameters:
          - ``VOLTAGE``

        Commands:
          - ``AUTO_RANGE``
        """

This happens at import time via ``__init_subclass__``, so Sphinx sees it without needing
to instantiate your control.

Complete Example
~~~~~~~~~~~~~~~~

Here's a more complete example:

.. code-block:: python

    from PyQt6.QtWidgets import QGroupBox, QGridLayout
    from hardware_control.base.gui_control import ValidatedControl
    from ..widgets import HCLabel, HCLineEdit, HCOnOffButton

    class PowerSupplyChannel(ValidatedControl, QGroupBox):
        """Control for a single power supply channel.

        This control provides voltage/current setting and readout,
        plus an on/off button.
        """

        # Declare all required parameters
        _required_parameters = [
            "CH1_V_SET", "CH1_I_SET", "CH1_ENABLE"
        ]
        _required_read_only = [
            "CH1_V_OUT", "CH1_I_OUT"
        ]
        _required_commands = ["CH1_RESET"]

        def __init__(
            self,
            app,
            instrument_name: str,
            widget_name: str = "Power Supply Channel"
        ):
            # Validation happens automatically
            super().__init__(app, instrument_name, widget_name)

            self.app = app
            self.instrument = instrument_name

            # Create widgets
            self.voltage_set = HCLineEdit(
                app, instrument_name, "CH1_V_SET",
                label="Voltage (V)"
            )

            self.current_set = HCLineEdit(
                app, instrument_name, "CH1_I_SET",
                label="Current (A)"
            )

            self.voltage_out = HCLabel(
                app, instrument_name, "CH1_V_OUT",
                label="V Out", unit="V"
            )

            self.current_out = HCLabel(
                app, instrument_name, "CH1_I_OUT",
                label="I Out", unit="A"
            )

            self.enable_button = HCOnOffButton(
                app, instrument_name, "CH1_ENABLE",
                label="Enable", show_icon=True
            )

            # Build layout
            layout = QGridLayout()
            layout.addWidget(self.voltage_set.label, 0, 0)
            layout.addWidget(self.voltage_set, 0, 1)
            layout.addWidget(self.voltage_out.label, 1, 0)
            layout.addWidget(self.voltage_out, 1, 1)
            layout.addWidget(self.current_set.label, 0, 2)
            layout.addWidget(self.current_set, 0, 3)
            layout.addWidget(self.current_out.label, 1, 2)
            layout.addWidget(self.current_out, 1, 3)
            layout.addWidget(self.enable_button, 2, 0, 1, 4)
            self.setLayout(layout)

Dynamic Parameters
~~~~~~~~~~~~~~~~~~

If your control has dynamic parameter names (e.g., multi-channel), you can build the
lists programmatically:

.. code-block:: python

    class MultiChannelControl(ValidatedControl, QGroupBox):
        """Control for multiple channels."""

        def __init_subclass__(cls, channels=None):
            """Build required parameters based on channels."""
            super().__init_subclass__()
            if channels:
                cls._required_read_only = [
                    f"CH{ch}_VOLTAGE" for ch in channels
                ]

Or use a class method factory:

.. code-block:: python

    @classmethod
    def for_channels(cls, channels):
        """Create a control class for specific channels."""
        # Build parameter lists
        read_only = [f"CH{ch}_VOLTAGE" for ch in channels]
        read_write = [f"CH{ch}_ENABLE" for ch in channels]

        # Create new class with those parameters
        return type(
            f"Control_{len(channels)}ch",
            (cls,),
            {
                "_required_read_only": read_only,
                "_required_parameters": read_write,
            }
        )

Important Notes
~~~~~~~~~~~~~~~

1. **Validation is automatic**: Just declare class attributes and call ``super().__init__()``
   with app and instrument_name. Validation happens there.

2. **All or nothing**: If any required parameter is missing, ``super().__init__()`` raises
   ValueError before your ``__init__`` body runs.

3. **Documentation is automatic**: The ``__init_subclass__`` hook adds parameter docs to
   your class docstring at class definition time.

4. **Use DeviceTemplate**: See ``DeviceTemplate.py`` for a complete working example.

Reference Implementation
~~~~~~~~~~~~~~~~~~~~~~~~

For complete examples, see:

- ``src/hardware_control/gui/controls/DeviceTemplate.py`` - Template with step-by-step comments
- ``src/hardware_control/gui/controls/FlowController.py`` - Simple two-parameter control
- ``src/hardware_control/gui/controls/MultiPowerSupply.py`` - Complex multi-channel control

API Reference
~~~~~~~~~~~~~

ValidatedControl
""""""""""""""""

.. py:class:: ValidatedControl

   Mixin for controls that validate instrument parameters.

   **Class Attributes** (declare in your subclass):

   .. py:attribute:: _required_parameters
      :type: list[str]

      Read/write parameters (both readable and writable)

   .. py:attribute:: _required_read_only
      :type: list[str]

      Read-only parameters (only readable)

   .. py:attribute:: _required_write_only
      :type: list[str]

      Write-only parameters (only writable)

   .. py:attribute:: _required_commands
      :type: list[str]

      Commands (no return value)

   **Methods**:

   .. py:method:: __init__(app, instrument_name, *args, **kwargs)

      Initialize and validate the control.

      Validation happens automatically here. If the instrument is missing any
      required parameters, ValueError is raised before the rest of your
      __init__ runs.

      :param app: The hardware control application instance
      :type app: App
      :param instrument_name: Name of the instrument this control interfaces with
      :type instrument_name: str
      :param args: Passed to parent class (typically widget title for QGroupBox)
      :param kwargs: Passed to parent class
      :raises ValueError: If instrument is missing required parameters/commands

Troubleshooting
~~~~~~~~~~~~~~~

**Problem**: ValueError says parameter is missing, but I know it exists in the instrument

**Solution**: Check the parameter name spelling and that it's in the correct list
(``_required_parameters`` vs ``_required_read_only``). The error message shows exactly
what the control requires and what the instrument provides.

----

**Problem**: I forgot to declare a parameter and got a runtime error

**Solution**: Add it to the appropriate class attribute list. The validation will catch
it on next instantiation.

----

**Problem**: How do I make a parameter optional?

**Solution**: Don't add it to the required lists. Just handle the case where
``app.get_instrument_parameter()`` returns ``None``.

----

**Problem**: My control needs different parameters depending on configuration

**Solution**: Use ``__init_subclass__`` or a class factory to build the parameter lists
dynamically. See "Dynamic Parameters" above.
