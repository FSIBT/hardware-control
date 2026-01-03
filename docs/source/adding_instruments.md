# Add a New Instrument

If there is an instrument you would like to use with Hardware Control
but no driver is available yet, you are encouraged to write your
own. If you are feeling generous, you can contribute it to Hardware
Control for future distributions (see contribution guidelines for
help)! Since most of the work is done in the base class, adding a new
instrument can be relatively straight forward. This step-by-step guide
is designed to help walk you through the process of creating a new
driver.

**Note:** If you're migrating from version 3.x, see the [Migration Guide](migration_guide.md)
for details on the new connection API introduced in version 4.0.0.

### 1. Start With a Template

Start by duplicating an existing driver for the same type of
instrument (e.g.  if you are adding a driver for a new oscilloscope,
the oscilloscope driver 'Keysight_4000X' for the Keysight 4000X
oscilloscope would be a good place to start).  This can help you get
off on the right foot with regard to common tasks such as writing
import statements, configuring logger, and adding parameters and
commands.

### 2. Implement the `__init__()` Function

The instrument base class (which all instrument drivers typically
inherit from) takes care of most things in the init function, but
there are still a few details that need to be written for your
specific instrument driver. A standard driver takes at least two
arguments -- an `instrument_name` and a `connection_address` -- which
need to be set or passed to the instrument base class using
`super().__init__(instrument_name, connection_addr)`. It is also nice
to set `self.manufacturer` and `self.model`, but this is not a
requirement.

After settings these basic variables, the main task is to define all
the possible commands and parameters that are available in the
instrument. This is done by using calls to `self.add_command` and
`self.add_parameter`. `self.add_command` requires that you define an
HC-specific name as a string (for example, `TRIGGER`) and a command
that will be passed to the instrument. `self.add_parameter` also
requires a name (for example, `CH1_VOLTAGE`) and has the option of
initializing two types of commands: a read command and a write command
for reading from and writing to an instrument, respectively. A
parameter can be initialized with a single read command, a single
write command, or both.

When defining these parameters and commands, you can also add custom
hooks that act before calling a command, before setting a value,
and/or after reading a value.

We also implemented a 'dummy' mode for instruments, in which they will
return pre-defined data (that can be random), which can be good for
debugging while not connected to any instruments. The return values
for 'dummy' mode can be set in the driver to either a constant value
or a python function (to, for example, return a random value). The
value can also later be overwritten by the user.

The reason we remap the instrument's command syntax to new command
names in the `add_parameter` and `add_command` functions is to ensure
that the widgets can base their UIs on generic command/parameter names
that can work for all instruments of a similar type. The driver's
purpose is to translate the generic commands to the syntax required
for your specific instrument. Because of this, if you plan on using
your driver with an existing Hardware-Control GUI, you will need to
make sure the `name` field in the calls to `add_parameter` and
`add_command` in your driver agrees with the corresponding names in
the widget interface that you intend to use.

Note that to get a usable instrument driver, you only need to
implement the commands and parameters you want to use. There is no
need to implement every command available to the instrument or the
widget (although this would be nice).

**Important:** When using `add_parameter()`, you must provide at least one of
`read_command` or `set_command`. The base class validates this and will log
an error if neither is provided.

### 3. Implement Connection Methods (If Needed)

*Changed in version 4.0.0*

Most instruments use the standard connection types (VISA, socket, modbus) and
don't need custom connection code. However, if your instrument requires special
connection handling (e.g., USB libraries, custom protocols), you should override
the connection methods.

**Important:** Do NOT override `try_connect()`. It uses the template method pattern
and manages connection state automatically. Override these methods instead:

#### `establish_connection()`

Override this to create your device connection. This is called by the base class
when the instrument is not yet online.

```python
def establish_connection(self):
    """Establish connection to the instrument.

    This method should:
    - Create self.device
    - Configure the connection
    - Return True on success, False on failure

    This method does NOT need to:
    - Check if already online (handled by base class)
    - Set self._online (handled by base class)
    - Close old connections (handled by cleanup_connection)
    """
    # Example: USB device using custom library
    self.device = my_usb_library.connect(self.device_id)
    return True  # or False if failed
```

#### `cleanup_connection()` (Optional)

Override this only if your device needs custom cleanup beyond calling `.close()`.

```python
def cleanup_connection(self):
    """Clean up connection resources."""
    if self.device is not None:
        self.device.shutdown()  # Custom cleanup
        self.device.release_hardware()
        self.device = None
```

#### `on_connect()` (Optional)

Override this to send initialization commands after the connection is established
and verified.

```python
def on_connect(self):
    """Send initialization commands after connection."""
    # Called AFTER establish_connection() succeeds
    # and AFTER check_connection() verifies it works
    self.device.clear_buffer()
    self.device.enable_user_mode()
```

**Benefits of the new API:**
- Automatic resource cleanup (no leaks)
- Automatic state management
- Automatic dummy mode handling
- Simpler, more focused code

See the [Migration Guide](migration_guide.md) for detailed examples and the
rationale behind this change.

### 4. Interfacing with the Instrument through Hardware-Control

To trigger a driver command, use `instance.command(<HC name of the
command>)`. You can read parameters with `instance[<HC name of
parameter>]` and set parameters with `instance[<HC name of
parameter>]=value`.
