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
