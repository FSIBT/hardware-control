Creating GUI Controls
=====================

This guide shows how to create custom GUI controls with automatic parameter validation.

Parameter Validation Pattern
-----------------------------

Hardware Control provides automatic validation to ensure instruments support all parameters
used by your GUI control. This prevents runtime errors when a parameter doesn't exist.

How It Works
~~~~~~~~~~~~

1. **Inherit from ValidatedControl**: Use it as first parent class
2. **Pass app and instrument_name to super().__init__()**: This auto-starts parameter collection
3. **HC widgets auto-register**: When you create HCLabel, HCLineEdit, etc., they automatically
   register their parameters
4. **Manual registration**: Parameters you use directly (not through widgets) must be added manually
5. **Validation**: Call ``_validate_parameters()`` after creating all widgets

Example: Simple Control
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
    from ..widgets import HCLabel, HCLineEdit
    from .base_control import ValidatedControl

    class SimpleVoltmeter(ValidatedControl, QGroupBox):
        def __init__(self, app, instrument_name: str, widget_name: str = "Voltmeter"):
            # 1. Pass app and instrument_name to super().__init__()
            #    This auto-starts parameter collection
            super().__init__(app, instrument_name, widget_name)

            self.app = app
            self.instrument = instrument_name

            # 2. Create widgets (they auto-register their parameters)
            self.voltage_display = HCLabel(
                app, instrument_name, "VOLTAGE",
                label="Voltage", unit="V"
            )  # Auto-registers "VOLTAGE" as readable parameter

            self.range_selector = HCLineEdit(
                app, instrument_name, "RANGE",
                label="Range"
            )  # Auto-registers "RANGE" as read/write parameter

            # 3. Manually add parameters used directly (not through widgets)
            # Example: if you call app.call_instrument_command() directly
            self._add_required_parameter("AUTO_RANGE", param_type='command')

            # 4. IMPORTANT: Validate everything (don't forget this!)
            self._validate_parameters()

            # Now safe to use - validation passed!
            layout = QVBoxLayout()
            layout.addWidget(self.voltage_display.label)
            layout.addWidget(self.voltage_display)
            layout.addWidget(self.range_selector.label)
            layout.addWidget(self.range_selector)
            self.setLayout(layout)

When to Manually Add Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add parameters manually when you use them **directly in code** without a widget:

.. code-block:: python

    # Reading directly
    voltage = self.app.get_instrument_parameter(self.instrument, "VOLTAGE")
    # → Add: self._add_required_parameter("VOLTAGE", access='read')

    # Setting directly
    self.app.set_instrument_parameter(self.instrument, "RANGE", "10V")
    # → Add: self._add_required_parameter("RANGE", access='write')

    # Calling command
    self.app.call_instrument_command(self.instrument, "AUTO_RANGE")
    # → Add: self._add_required_parameter("AUTO_RANGE", param_type='command')

**You DO NOT need to add parameters that are already used in HC widgets!**

Error Messages
~~~~~~~~~~~~~~

If validation fails, you get a clear error message:

.. code-block:: text

    ValueError: Instrument 'DMM_1' missing required parameters/commands for SimpleVoltmeter:
      - AUTO_RANGE (command)
      - VOLTAGE (readable)

    Required: ['VOLTAGE', 'RANGE', 'AUTO_RANGE']

This tells you exactly what's missing and helps debug instrument compatibility issues.

Auto-Generated Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you call ``_validate_parameters()``, the required parameters are automatically
documented in the class docstring! This appears in the Sphinx-generated docs:

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

No need to manually maintain this list - it's always up to date!

Complete Example
~~~~~~~~~~~~~~~~

Here's a more complete example showing all the features:

.. code-block:: python

    from PyQt6.QtWidgets import QGroupBox, QGridLayout
    from .base_control import ValidatedControl
    from ..widgets import HCLabel, HCLineEdit, HCOnOffButton

    class PowerSupplyChannel(ValidatedControl, QGroupBox):
        """Control for a single power supply channel.

        This control provides voltage/current setting and readout,
        plus an on/off button.
        """

        def __init__(
            self,
            app,
            instrument_name: str,
            channel: int,
            widget_name: str = "Power Supply Channel"
        ):
            # Auto-starts parameter collection
            super().__init__(app, instrument_name, widget_name)

            self.app = app
            self.instrument = instrument_name
            self.channel = channel

            # HC widgets auto-register their parameters
            self.voltage_set = HCLineEdit(
                app, instrument_name, f"CH{channel}_V_SET",
                label="Voltage (V)"
            )  # Auto-registers CH{channel}_V_SET as read/write

            self.current_set = HCLineEdit(
                app, instrument_name, f"CH{channel}_I_SET",
                label="Current (A)"
            )  # Auto-registers CH{channel}_I_SET as read/write

            self.voltage_out = HCLabel(
                app, instrument_name, f"CH{channel}_V_OUT",
                label="V Out", unit="V"
            )  # Auto-registers CH{channel}_V_OUT as read-only

            self.current_out = HCLabel(
                app, instrument_name, f"CH{channel}_I_OUT",
                label="I Out", unit="A"
            )  # Auto-registers CH{channel}_I_OUT as read-only

            self.enable_button = HCOnOffButton(
                app, instrument_name, f"CH{channel}_ENABLE",
                label="Enable", show_icon=True
            )  # Auto-registers CH{channel}_ENABLE as read/write

            # Manually add command used in code below
            self._add_required_parameter(
                f"CH{channel}_RESET",
                param_type='command'
            )

            # IMPORTANT: Validate before using commands!
            self._validate_parameters()

            # Now safe to use command - we know it exists
            # (For example, reset channel on initialization)
            # self.app.call_instrument_command(
            #     self.instrument,
            #     f"CH{self.channel}_RESET"
            # )

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

Important Notes
~~~~~~~~~~~~~~~

1. **Don't forget _validate_parameters()**: This is the only manual step. Without it,
   validation won't happen and docs won't be generated.

2. **Call it after all widgets**: Make sure all HC widgets are created and all manual
   parameters are added before calling ``_validate_parameters()``.

3. **Use DeviceTemplate**: See ``DeviceTemplate.py`` for a complete working example
   showing the correct pattern with step-by-step comments.

4. **Validation happens once**: The ``_validate_parameters()`` method is idempotent -
   you can call it multiple times safely, but it only validates on the first call.

Advanced: Adding Parameters Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you create widgets in a loop, they auto-register correctly:

.. code-block:: python

    class MultiChannelControl(ValidatedControl, QGroupBox):
        def __init__(self, app, instrument_name, channels):
            super().__init__(app, instrument_name, "Multi-Channel Control")

            self.app = app
            self.instrument = instrument_name
            self.channels = channels
            self.widgets = []

            # Create widgets in a loop - they all auto-register!
            for channel in channels:
                voltage = HCLabel(
                    app, instrument_name, f"CH{channel}_VOLTAGE",
                    label=f"CH{channel} Voltage"
                )
                # Auto-registers CH{channel}_VOLTAGE as read-only
                self.widgets.append(voltage)

            # Validate all auto-registered parameters
            self._validate_parameters()

            # Build layout
            layout = QGridLayout()
            for i, widget in enumerate(self.widgets):
                layout.addWidget(widget.label, i, 0)
                layout.addWidget(widget, i, 1)
            self.setLayout(layout)

Reference Implementation
~~~~~~~~~~~~~~~~~~~~~~~~

For a complete, annotated reference implementation, see:

- ``src/hardware_control/gui/controls/DeviceTemplate.py`` - Template with step-by-step comments

For real-world examples, see:

- ``src/hardware_control/gui/controls/KeysightPowerSupply.py`` - Example with manual command registration
- ``src/hardware_control/gui/controls/FlowController.py`` - Simple control with only widget auto-registration
- ``src/hardware_control/gui/controls/MultiPowerSupply.py`` - Complex multi-channel control

API Reference
~~~~~~~~~~~~~

ValidatedControl Methods
""""""""""""""""""""""""

.. py:class:: ValidatedControl

   Mixin for controls that validate instrument parameters.

   .. py:method:: __init__(app, instrument_name, *args, **kwargs)

      Initialize the validation system.

      :param app: The hardware control application instance
      :type app: App
      :param instrument_name: Name of the instrument this control interfaces with
      :type instrument_name: str
      :param args: Passed to parent class (typically widget title for QGroupBox)
      :param kwargs: Passed to parent class

   .. py:method:: _add_required_parameter(parameter, param_type='parameter', access='read_write')

      Manually add a required parameter not used through a widget.

      :param parameter: Parameter or command name
      :type parameter: str
      :param param_type: Type of parameter - 'parameter' or 'command'
      :type param_type: str
      :param access: Access pattern - 'read', 'write', or 'read_write' (only for param_type='parameter')
      :type access: str

   .. py:method:: _validate_parameters()

      Validate that instrument provides all required parameters.

      This method MUST be called after creating all widgets and adding manual parameters.
      It performs validation and auto-generates documentation.

      :raises ValueError: If instrument is missing required parameters/commands

HC Widget Auto-Registration
""""""""""""""""""""""""""""

All HC widgets (HCLabel, HCLineEdit, HCComboBox, HCDoubleSpinBox, HCOnOffButton, etc.)
automatically register their parameters when created inside a ValidatedControl.

**Read-only widgets** (auto-register as ``access='read'``):

- HCLabel
- HCFixedLabel
- HCOnOffIndicator

**Read-write widgets** (auto-register as ``access='read_write'``):

- HCLineEdit
- HCComboBox
- HCDoubleSpinBox
- HCSpinBox
- HCOnOffButton
- All other HC widgets

Troubleshooting
~~~~~~~~~~~~~~~

**Problem**: ValueError says parameter is missing, but I know it exists in the instrument

**Solution**: Check the parameter name spelling. The error message shows exactly what
the control is looking for and what the instrument provides.

----

**Problem**: Validation passes, but I get errors at runtime when using a parameter

**Solution**: Make sure you added the parameter with ``_add_required_parameter()`` if
you're using it directly (not through a widget).

----

**Problem**: I want to make validation optional for testing

**Solution**: The validation is strict by design to catch errors early. For testing,
use a mock instrument that provides all required parameters.

----

**Problem**: My control has many channels and the auto-documentation is very long

**Solution**: This is expected - the auto-generated docs show all required parameters.
If you want to shorten it, you can override the docstring after ``_validate_parameters()``
is called.
