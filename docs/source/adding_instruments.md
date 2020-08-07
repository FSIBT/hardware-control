# Add a New Instrument Backend

If there is an instrument you'd like to use with Hardware Control but no backend
is available yet, you are encouraged to make your own backend. If you're feeling
generous, you can contribute it to hardware control for future distributions
(see contribution guidelines for help)! Since most of the work is done in the
base class, adding a new instrument can be relatively straight forward. This
step-by-step guide is designed to help walk you through the process of creating
a new backend.

### 1. Start with a Template

Starting by duplicating an existing backend for the same type of instrument (ie.
if you're adding a backend for a new oscilloscope, the oscilloscope backend
'Key4000XCtrl' would be a good place to start). This can help you get off on the
right foot with basics like the correct import statements, configuring the
logger, and having example functions.

### 2. Implement the `__init__()` Function

The base class takes care of most things in the init function, however there are
still a few details you need to manually fix. You'll need to make sure that any
default arguments, instrument ID strings, or similar parameters are appropriate
for the new instrument model. Often this will just mean changing the
instrument_name argument when the parent class is initialized in
`super().__init__()`.

### 3. Implement `update_setting()` and `command()`

The `update_setting()` and `command()` functions are where most of the work will
happen. These functions are called by the `HC_Comm` class, which relays
information between the frontend and backend. The function `update_setting()`
receives two strings are arguments, a parameter to adjust and a value, and
sends a command to the instrument to update this parameter with the new value.
An example of where this function would be used is in changing the timescale of
an oscilloscope. The `command()` function receives only a single string which
represents the name of an action to perform. For example, `commmand()` receives
the message "SINGLE_TRIGGER" to initiate a single trigger in an oscilloscope.

In these functions, the main body of the code you will need to write is a series
of if-statements. Each statement will check for a specific command to setting,
then communicate that command to the instrument using the appropriate syntax for
the specific instrument model.

Many settings will be sent in the format "CH\<X\>\_\<parameter\>", such as the
"CH1_volts_div" setting for oscilloscope models. Hardware Control defines the
function `get_channel_from_command(setting:str)` to easily process commands of
this format. Using a line such as:

`channel, setting_X = get_channel_from_command(setting)`

will allow you to easily get the string representing the channel number and the
parameter with the channel number replace with an 'X'. You can then process
commands for any channel by replacing the channel number with an "X":

<pre><code>channel, setting_X = get_channel_from_command(setting)

if setting_x == "CHX_volts_div":
	#Change volts per division setting for channel 'channel'</code></pre>

There are two ways to determine which commands and parameters need to be
implemented in `update_setting()` and `command()`. You can copy the
`update_setting()` and `command()` functions from a different backend for the
same instrument type as your backend and see which cases the original backend
covered. The potential risk of the copy method is that some backends cannot
implement all features present in the widget. For example, if you write a
backend for a four channel oscilloscope but use a two channel oscilloscope as a
template, there could be features regarding the two additional channels that you
do not see. The alternative way is to read the documentation for the frontend
widget of the instrument type you're interested in.

### 4. Querying Data

The front end can instrument the instrument to read back data using the
`command()` function described above. These query operations are slightly more
nuanced than other commands because they need to return data to be recorded by
the frontend. Hardware control uses a convention of adding question marks or
equal signs to indicate queries and measured data. Queries are sent to `command()` and follow the format `<parameter>?`. For example, "CH1_V_set?" is used by power supply
widgets to read the instrument's channel 1 set voltage. The data is returned in
the format `<parameter>=<value>`. A return string for the "CH1_V_set?" query
could be "CH1_V_set=1.0" for a 1V set voltage.

Some instruments use the function `command_listdata()` in addition to
`command()`. These two functions perform the exact same role of executing a
command specified by a string, except `command()` returns a single string and
`command_listdata()` returns a tuple of a string and two lists. This allows
you to avoid packaging large lists of data into strings to send them to the
frontend. Most query operations do not require the added complexity of
`command_listdata()` and can simply use `command()`, but others such as the
oscilloscope when it queries a series of waveforms from the instrument can
benefit substantially by transferring the data as a list. The easiest way to
determine if your instrument needs to implement `command_listdata()` is to see
if it is implemented in other backends of the same instrument type as yours.
