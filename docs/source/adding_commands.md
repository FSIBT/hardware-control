# Add New Command to Existing Backend

Not all commands are currently implemented in all instruments drivers. If you want to
add a command that is not yet implemented, this guide will show you how.

### 1. Identify Command Syntax

We distinguish between two different types: commands and parameters. A
command is something like 'trigger' that doesn't create an output and
we define a parameter as a value that can be read or written to. For
any of these cases you need to find what you need to send to the
instrument from the manual. For socket connections over TCP these are
normally just ascii strings, which is true for most other cases too.

### 2. Identify Name in an existing GUI widget

If you want to be able to reuse an existing GUI widget, you need to
figure out what the name is that this parameter maps to. For example,
for a power supply, we use the name `CH1_V_OUT` to describe the actual
voltage for CH1. If you write a new GUI, you can come up with a name
you want here. The name needs to be unique for the instrument. Next
you use the built-in function of an `Instrument` class
`self.add_parameter` or `self.add_command` to link the name to the
actual command. At this point you can also define some function that
can be added as a hook before setting a value. These can be used, for
example, to scale a voltage from the real value to a 0-10 V scale. You
can also define hooks for post-processing a value when it is read to
go then, for example, from a 0-10 V back to the real applied voltage.

These hooks can also be used for validation and to check ranges, etc.
If a hook returns `None` the value will not be set or returned or a
command will not be called.


### What if the Feature I'm Adding is not Implemented in the GUI?

If the command you're adding to your instrument is not yet implemented in the
corresponding GUI, then you will need to add a widget to the frontend GUI
which allows you to control your new command. For guidance on this, view the
instructions on how to create a new user interface.
