# Add A New User Interface

If there's an instrument type you'd like to use with Hardware Control but no
user interface is available yet, or if you'd like to make an alternative
interface to better suit your needs, you can add your own. If you're familiar
with using Qt it is relatively easy to make a new interface. This
step-by-step guide is designed to help walk you through the process of creating
a new interface/frontend.


### 1. Start with a Template

Starting by duplicating an existing interface can help you see exactly which
functions you'll need to define in your interface class.

### 2. Define the GUI in` __init__()`

The GUI is defined inside the `__init__()` function. If you're creating an
interface with repeated elements such as the channel controls of an
oscilloscope, it's recommended to create a class which implements that
subsection of your UI. This makes it easy to change all of the repeated elements
in the future or add and remove them to the main UI. If you need help with Qt,
in addition to the Qt documentation and tutorials online, you can look at user
interfaces defined in Hardware Control. Most interfaces consist of only a few
widgets such as QLineEdit, QLabel, and QComboBox. You'll see how to use them and
how to add them to a QGridLayout by examining the interfaces classes in
Hardware Control.

### 3. Connect GUI to `update_setting()` and `command()`

Unless your interface only displays data and doesn't send instructions to your
instrument, the widgets you created in the GUI will need to be able to send
instructions to the backend. This is accomplished by connecting PyQtSignals to
callback functions. The example below shows the PyQtSignal 'editingFinished'
being connected to the callback function `update_setting()` and providing the
appropriate arguments (the arguments being the setting "CH\<x\>\_amplitude" and
the value in the QLineEdit)

<pre><code>self.amplitude_edit = QLineEdit()
self.amplitude_edit.editingFinished.connect(
	lambda: control.update_setting(
		f"CH{channel}_amplitude", (self.amplitude_edit.text())
	)
)
</pre></code>

### 4. Implement `default_state()` to define settings dictionary

The dictionary `settings` is defined in the `Instrument` base class and used to
track the state of the parameters tracked by the widget. The `default_state()`
function creates the initial value for `settings`. After `settings` is
initialized in `default_state()`, it is not expected to have new keys entered.

When you define the `default_state` function, you need to add every parameter
that you want to have visible to the rest of the application or that you want to
have updated in the UI. This is because the `settings` dictionary is used in
many places such as the `setting_to_UI()` function which allows Hardware Control
to programmatically update the user interface, or in the Scan Widget which can
only scan through parameters listed in `settings`.

### 5. Implement `settings_to_UI()`

`settings_to_UI()` updates the widgets in the user interface for a specific
instrument with the values in the instrument's `settings` dictionary.
