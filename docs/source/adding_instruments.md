# Add a New Instrument

If there is an instrument you'd like to use with Hardware Control but no driver
is available yet, you are encouraged to write your own. If you're feeling
generous, you can contribute it to hardware control for future distributions
(see contribution guidelines for help)! Since most of the work is done in the
base class, adding a new instrument can be relatively straight forward. This
step-by-step guide is designed to help walk you through the process of creating
a new driver.

### 1. Start with a Template

Starting by duplicating an existing driver for the same type of instrument (ie.
if you're adding a driver for a new oscilloscope, the oscilloscope driver
'Key4000XCtrl' could be a good place to start). This can help you get off on the
right foot with basics like the correct import statements, configuring the
logger, and having example functions.

### 2. Implement the `__init__()` Function

The base class takes care of most things in the init function, however
there are still a few details you need to manually fix. A standard
driver takes a `instrument_name` and `connection_address` argument
that need to be set or passed to the base class using
`super().__init__(instrument_name, connection_addr)`.  It is also nice
to set `self.manufacturer` and `self.model`, but this is not a must.

After settings these basic variables, the main task is to define all
the possible commands and parameters that are available in the
instrument. This is done by using calls to `self.add_parameter` and
`self.add_command`. Here you define a HC specific string, for example,
`CH1_VOLTAGE`, and connect them with, for example, the read and write
command that are needed to be send to the instrument to change or read
this value.

When defining these parameters and commands, you can also add custom
hooks that act before calling a command, setting a value or after
reading a value.

We also implemented a 'dummy' mode for instruments, where they will
return pre-defined data (that can be random), which can be good for
debugging.

The reason we remap the instrument's command syntax to new command names in the
`add_parameter` and `add_command` functions is to ensure that the widgets can
base their UIs on generic command/parameter names that can work for all instruments
of one type. The driver's purpose is to translate the generic commands to the
syntax required for your specific instrument. Because of this, if you plan on
using your driver with an existing Hardware-Control GUI, you will need to make
sure the `name` field in the calls to `add_parameter` and `add_command` in your
driver agrees with the corresponding names in the widget's interface.

Note that to get a usable instrument driver, you only need to implement the
commands and parameters you want to use. There is no need to implement every
command available to the instrument or the widget (although this would be nice).

### 3. Interfacing with the Instrument through Hardware-Control

To trigger a driver command, use `instance.command(<HC name of the
command>)`. You can read parameter with `instance[<HC name of parameter>]` and
set parameters with `instance[<HC name of parameter>]=value`.
