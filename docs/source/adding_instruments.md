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

The reason to define a HC custom string is to be able to make our GUIs
reusable. Therefore, if you want to use one of the pre-defined GUIs,
you should choose the HC names in according to the GUI you want to
use.

To get a usable instrument driver, you only need to implement the
commands and parameter you want to use and don't have to implement
everything (which of course would be nice).

### 3. Querying Data directly from the Instrument

To call a commands you just do `instance.command(<HC name of the
command>)` and to read a value `instance[<HC name of parameter>]`
works. Setting a value can also be done easily by using `instance[<HC
name of parameter>]=value`.

