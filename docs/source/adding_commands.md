# Add New Command to Existing Backend

Not all commands are currently implemented for all instruments. If you want to
add a command that is not yet implemented, this guide will show you how.

### 1. Identify Command Syntax

The widgets in the frontend pass information and commands to the backend via
strings. To add a command to the backend that already has a control in the
frontend, you need to examine the class for the frontend interface and find the
string it sends to the backend to indicate that the operation you're adding is
being triggered. For example, if you wanted to add single trigger functionality
to an oscilloscope model that did not have this feature implemented in its
backend, you would need to open the frontend, Oscilloscope.py, and identify
where the single trigger command occurs. You would find it calls `command()` and
passes the string `SINGLE_TRIGGER` as its argument. This is what you will need
to detect in the backend that you are modifying.

### 2. Add Command to Backend

After identifying how the frontend is communicating the instruction to the
backend (ie. via `update_setting()`, `command()`, or `command_listdata()` and
with what string arguments) you can handle that command in your backend. You
will need to go to the function in your backend that is being called via the
frontend (in our example above that would be the function `command()`) and add
an if-statement that looks for the string indicating the command you're adding
was sent. An example of what this could look like is:

<pre><code> if command == "SINGLE_TRIGGER":
	# Instruct instrument to single trigger
</pre></code>

### What if the Feature I'm Adding is not Implemented in the GUI?

If the command you're adding to your backend is not yet implemented in the
corresponding frontend, then you will need to add a widget to the frontend GUI
which allows you to control your new command. For guidance on this, view the
instructions on how to create a new user interface.
