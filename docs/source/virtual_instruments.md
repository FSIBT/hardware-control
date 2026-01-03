# Virtual Instruments

*New in version 4.0.0*

Virtual instruments allow you to integrate data from non-hardware sources into the Hardware Control framework. They work seamlessly with all existing features including widgets, datasets, alarms, and hooks.

## What are Virtual Instruments?

Virtual instruments are data sources without physical hardware connections. They're useful for:

- **Web APIs**: Pull data from weather services, stock prices, or other online sources
- **Calculations**: Display computed values derived from other instruments
- **User Input**: Accept manual data entry through GUI elements
- **External Systems**: Integrate data from databases, file systems, or other applications

Unlike hardware instruments, virtual instruments:
- Don't require connection addresses
- Don't attempt network/USB connections
- Don't have ZMQ adapters or threads
- Are updated explicitly via `update_virtual_instrument_parameter()`

## Creating a Virtual Instrument

Use `app.add_virtual_instrument()` to create a virtual instrument:

```python
# Create a virtual instrument with two parameters
app.add_virtual_instrument("Weather", ["temperature", "humidity"])
```

This creates an instrument called "Weather" with two parameters that can be read and displayed.

## Updating Parameters

Update virtual instrument parameters using `app.update_virtual_instrument_parameter()`:

```python
# Update from a web API
import requests
data = requests.get("https://api.weather.com/...").json()
app.update_virtual_instrument_parameter("Weather", "temperature", data["temp"])
app.update_virtual_instrument_parameter("Weather", "humidity", data["humidity"])
```

When you update a parameter, the framework automatically:
1. Applies any `post_read_hooks` to the value
2. Updates the stored value
3. Triggers alarm checks via `alarm_manager`
4. Updates all registered widgets (HCLabels, etc.)

## Using with Widgets

Virtual instruments work with all standard Hardware Control widgets:

```python
# Create an HCLabel to display the temperature
temp_label = hc.gui.widgets.HCLabel(
    app, "Weather", "temperature", "Temperature:"
)

# The label automatically updates when you call update_virtual_instrument_parameter()
```

## Using with Datasets

Virtual instruments can be logged in datasets just like hardware instruments:

```python
# Create a dataset
dataset = hc.Dataset("weather_data", app)

# Track virtual instrument parameters
dataset.track_instrument("Weather", "temperature", alias="Temp (°C)")
dataset.track_instrument("Weather", "humidity", alias="Humidity (%)")

# Start automatic updates
dataset.start_updates(interval=2)  # Update every 2 seconds

# Add to app
app.add_dataset(dataset)
```

## Using with Hooks

Add formatting or validation hooks to virtual instrument parameters:

```python
# Add a formatting hook to show 2 decimal places
app.add_hook(
    "Weather",
    "temperature",
    "post_read_hooks",
    hc.hooks.format_float(".2f")
)

# Now all updates will be formatted
app.update_virtual_instrument_parameter("Weather", "temperature", 25.345678)
# Displayed as: "25.35"
```

## Using with Alarms

Virtual instruments support alarms just like hardware instruments:

```python
# Create an alarm for high temperature
app.alarm_manager.add_alarm(
    hc.Alarm(
        "Weather",
        "temperature",
        "High Temperature",
        ">",
        30,  # threshold
        0,   # duration
        action="alarm.wav"
    )
)
```

## Complete Example

Here's a complete example showing random number generation and user input:

```python
import random
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget
import hardware_control as hc

class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        # Create virtual instrument
        self.app.add_virtual_instrument("DataSource", ["random_value", "user_input"])

        # Add formatting hook
        self.app.add_hook(
            "DataSource", "random_value", "post_read_hooks",
            hc.hooks.format_float(".2f")
        )

        # Create widgets that automatically update
        self.random_label = hc.gui.widgets.HCLabel(
            self.app, "DataSource", "random_value", "Random:"
        )
        self.input_label = hc.gui.widgets.HCLabel(
            self.app, "DataSource", "user_input", "User Input:"
        )

        # User input field
        self.line_edit = QLineEdit()
        self.line_edit.editingFinished.connect(self.update_user_input)

        # Set up timer for random updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_random)
        self.timer.start(1000)  # Every second

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.random_label)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.input_label)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.show()

    def update_random(self):
        """Called every second by timer."""
        value = random.uniform(0, 100)
        self.app.update_virtual_instrument_parameter(
            "DataSource", "random_value", value
        )

    def update_user_input(self):
        """Called when user finishes editing."""
        try:
            value = float(self.line_edit.text())
            self.app.update_virtual_instrument_parameter(
                "DataSource", "user_input", value
            )
        except ValueError:
            pass  # Ignore invalid input

# Run the application
main_window = Demo(dummy=False)
sys.exit(main_window.app.exec_())
```

## API Reference

### `App.add_virtual_instrument(instrument_name, parameters)`

Create a virtual instrument.

**Parameters:**
- `instrument_name` (str): Name of the virtual instrument
- `parameters` (list[str]): List of parameter names to create

**Example:**
```python
app.add_virtual_instrument("Calculations", ["average", "sum", "max"])
```

### `App.update_virtual_instrument_parameter(instrument, parameter, value)`

Update a virtual instrument parameter value.

**Parameters:**
- `instrument` (str): Virtual instrument name
- `parameter` (str): Parameter name
- `value` (Any): New value (will be converted to string after hooks)

**Example:**
```python
app.update_virtual_instrument_parameter("Calculations", "average", 42.5)
```

## See Also

- Complete working example: `examples/virtual_instrument.py`
- [Adding Instruments](adding_instruments.md) - For hardware instruments
- [Using Hardware Control](using_hardware_control.md) - General usage guide
