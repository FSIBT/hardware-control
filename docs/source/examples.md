Examples
========

We provide several examples applications that highlight some of the
functionality or just show the different controls that can be used for
the instrument driver we have.

If you have the same hardware you will have to update the instrument
address in the example code to run them. In case you want to run them
without any hardware connected, you should add `--dummy` to the
command line, which will start them in dummy mode.

To get logging output you can add `--console` to reroute the logging
error to the console (otherwise it will go into a file in the
directory you are running the code). You can also change the loglevel
to `--info` or if you want a lot more output to `--debug`.

## Featured Examples

### Virtual Instrument Demo

**File:** `examples/virtual_instrument.py`

Demonstrates virtual instruments for integrating non-hardware data sources
(web APIs, calculations, user input) into the Hardware Control framework.

**Features:**
- Random number generator updating a virtual parameter every second
- User input via QLineEdit updating another virtual parameter
- HCLabels automatically displaying both parameters
- Dataset tracking and plotting values over time
- Full integration with hooks, alarms, and widgets

**Usage:**
```bash
python examples/virtual_instrument.py --dummy --console
```

**What you'll learn:**
- Creating virtual instruments with `app.add_virtual_instrument()`
- Updating parameters with `app.update_virtual_instrument_parameter()`
- How virtual instruments work seamlessly with existing widgets
- Logging virtual instrument data in datasets

### Dataset and Plotting

**File:** `examples/dataset_plotting.py`

Shows how to create datasets, track instrument parameters over time,
and display data in plots.

### Alarms

**File:** `examples/alarm.py`

Demonstrates the alarm system with audio notifications when parameters
exceed thresholds.

### Hooks

**File:** `examples/hooks.py`

Shows how to use hooks to transform data, validate inputs, and trigger
custom actions based on parameter values.

### ONLINE Hook - Connection Event Tracking

**File:** `examples/online_hook.py`

Demonstrates using a hook on the special `ONLINE` parameter to track when
instruments connect and disconnect.

**Features:**
- Tracks connection/disconnection events with timestamps
- Logs connection history
- Updates UI elements based on online status
- Shows how to run custom code when instruments come online

**Important:** This example does NOT work in dummy mode. You need a real
instrument that you can power on/off to see the connection events.

**Usage:**
```bash
# Edit the file first to set your instrument address
python examples/online_hook.py --console
```

**What you'll learn:**
- Using hooks on the `ONLINE` parameter
- Tracking instrument connection state
- Updating UI based on connection events
- Difference between hooks in app vs. `on_connect()` in drivers

