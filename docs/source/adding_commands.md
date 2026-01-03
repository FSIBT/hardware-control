# Add a New Command to Existing Backends

Almost all instruments have commands that are not currently implemented in our instruments
drivers. If you want to add a command to an instrument that is not yet implemented,
this guide will show you how.

### 1. Identify Instrument Syntax

In Hardware Control we distinguid between two different ways of
communicating with an instrument: _commands_ and _parameters_. A
_command_ tells the instrument to perform some action but does not
produce a value to read back. An example of a command would be
triggering an oscilloscope.  A _parameter_ is something that can be read
or written to, such as the output voltage of a power supply. For both,
sending commands and reading or writing parameters, you need to
determine the correct syntax for communicating with the instrument
from the instrument's manual. In most cases, these are just ASCII
strings, often in the form of SCPI instructions.

### 2. Linking to an Existing GUI Widget

Once you have added your command or parameter to the instrument driver, you need to
link it to a control or readout in the GUI widget. The `add_parameter` or `add_command`
functions used in your instrument driver require a name. That name is what the
GUI widgets will use to determine which values to set or read back when they interact
with the driver. If you want to connect your new backend instruction to an existing
GUI widget, you need to ensure that the name of your command/parameter matches that
referenced by the GUI. Note that a command/parameter names cannot be repeated
within the same instrument.

If the command you are adding to your instrument is not yet implemented in a
corresponding GUI, you will need to add a widget to the frontend GUI that allows
you to interface with your new command/parameter. For guidance on this, view the
instructions on how to create a new user interface.

### 3. Hooks

You can add pre-hooks or post-hooks to operate on values passed from the GUI to
the backend or from the backend to the GUI, respectively. This is often useful if
the values shown on the GUI need to be scaled or otherwise translated in order to
communicate with the instrument. For example, if a power supply was interfaced
using a control voltage that was scaled by a factor of 10 from the actual output
voltage, you could display the output voltage on the widget, then use a pre and
post hook to translate the display voltage to the scaled control voltage.

Hooks can also be used for validation, such as checking that a value is within a
specified range. If a hook returns `None`, the parameter value will not be set/returned,
or the command will not be sent.

### 4. Triggering Actions When Instruments Come Online

*New in version 4.0.0*

Every instrument has a special read-only parameter called `ONLINE` that indicates
whether the instrument is connected and communicating. You can attach a `post_read_hooks`
to this parameter to trigger custom actions whenever an instrument's online status changes.

This is useful for:
- Sending initialization commands when an instrument connects
- Updating UI elements based on connection status
- Logging connection events
- Re-configuring settings after reconnection

**Example: Call a function when instrument comes online**

```python
class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        # Add instrument
        power_supply = hc.instruments.Keysight_36300("ps1", "192.168.0.10")
        self.app.add_instrument(power_supply)

        # Add hook to ONLINE parameter
        self.app.add_hook(
            "ps1",
            "ONLINE",
            "post_read_hooks",
            self.on_instrument_online
        )

    def on_instrument_online(self, online_status):
        """Called whenever the online status changes."""
        # online_status is "True" or "False" (as string)
        if online_status == "True":
            print("Power supply is now online!")
            # You could send initialization commands here
            # Or update GUI elements
            # Or enable/disable controls
        else:
            print("Power supply went offline")

        # IMPORTANT: Always return the value to allow other hooks
        # and widgets to process it
        return online_status
```

**Important Notes:**

- The `ONLINE` parameter is updated automatically by the framework during connection attempts
- Your hook function receives the online status as a string: `"True"` or `"False"`
- **Always return the value** from your hook to allow the framework to continue processing
- The hook is called every time the parameter is read, which happens during connection checks
- For one-time initialization, you may want to track whether you've already initialized:

```python
def __init__(self, dummy):
    super().__init__(dummy=dummy)
    self.initialized = False
    # ... rest of init ...

def on_instrument_online(self, online_status):
    """Only run initialization once when first coming online."""
    if online_status == "True" and not self.initialized:
        print("First time online - running initialization")
        # Send initialization commands
        self.app.set_instrument_parameter("ps1", "VOLTAGE", 5.0)
        self.initialized = True
    return online_status
```

**Alternative: Using `on_connect()` in Custom Drivers**

If you're writing a custom instrument driver and need to send commands immediately
after connection, it's better to override the `on_connect()` method in your driver
class rather than using hooks:

```python
class MyInstrument(Instrument):
    def on_connect(self):
        """Called automatically after connection is established."""
        # Send initialization commands here
        self.device.clear_buffer()
        self.device.set_mode("safe")
```

See the [Adding Instruments](adding_instruments.md) guide for more details on
the `on_connect()` method.

**Complete Example**

See `examples/online_hook.py` for a complete working example that demonstrates:
- Tracking connection/disconnection events
- Logging timestamps when instruments come online
- Displaying connection history
- Updating UI elements based on online status

Note: This example requires a real instrument (does not work in dummy mode).
