# Write a Control Program

Hardware Control supplies a collection of widgets and backends for controlling
instruments. This guide will walk you through setting up a simple control
program using Hardware Control.

### 1. Import Hardware Control

Once installed (see installation instruction if you need help), you can import
Hardware Control with only two lines:

<pre><code>import hardware_control.backends as hc_back
import hardware_control.gui as hc</pre></code>

Now you can access any backend with `hc_back.<backend_class_name>` and all other
classes, including the user interfaces, with `hc.<class_name>`.

### 2. Create an App Class

Hardware Control uses Qt to create windows and graphics. Qt applications expect
the user to create a class which inherits from QMainWindow. To create your
Hardware Control program, you must also create a class and inherit from
MainWindow, Hardware Control's window class which inherits from QMainWindow. The
class would start off looking like:

<pre><code>class DemoProgram (hc.MainWindow):
    def __init__(self, app):

		super().__init__([])
</code></pre>

### 3. Create and Add Instruments

The focus of your program will be on creating backends to communicate with the
instrument, frontends or interfaces which contain the widgets and GUI elements
to let you interact with your instrument, and adding them to your window.

1. Create a Backend

	To create a backend, find the appropriate backend class and initialize it with
	the address of your instrument. Depending on the backend class, the type of
	address can change. Most backends accept IP addresses, but others might use
	alternative protocols such as USB, MODBUS or GPIB. You'll need to check your
	backend's documentation to make sure you configure it correctly.

	`scope_be = hc_back.Keysight_4000X("192.168.0.2")`

2. Create a Control Widget

	The control widget or frontend will communicate with your backend. To create the
	control widget, create an object of the control widget class and pass the
	backend you want it to control as an argument.

	`self.scope_wdgt = hc.Oscilloscope(scope_be, self, "Oscilloscope")`

3. Add Widget to Layout

	Finally, you must add the control widget to a layout. Qt offers multiple
	ways for arranging layouts, but in this example we'll look at the
	QGridLayout. To add your widget to a layout, you must create the layout
	object, then use `addWidget()` to add your control widget to the layout
	at the specified position.

	<pre><code># Create layout, add oscilloscope to row=0, column=0
self.main_layout = QGridLayout()
self.main_layout.addWidget(self.scope_wdgt, 0, 0)
</pre></code>

Putting together all three steps is how you add an instrument to your control
program. By repeating these steps you can add an indefinite number of
instruments and build complicated control programs with minimal code.

### 4. Prepare your Window to Display

You need to tell your window what to display and when. An easy way to do this is
to create a new QWidget, Qt's base widget class, and set it to use the layout
you added your control widgets to. You can then set this new QWidget to be the
central widget for your window. The last thing you need to do is add a call to
`self.show()` at the end of your `__init__()` function to tell Qt to display the
window.

<pre><code>self.main_widget = QWidget(self)
self.main_widget.setLayout(self.main_layout)
self.setCentralWidget(self.main_widget)

self.show()</pre></code>


### 5. Create Instance of Your Class and App

The next step is to create an instance of your class. To do this, however you
must pass in an App object. Hardware Control provides an App class which
facilitates communication between instruments, along with a number of other
features such as centralized data collection and menu bars. Create an instance
of App and pass it to the class you defined for your program.

<pre><code>app = hc.App()
demo_prog = DemoProgram(app)
</pre></code>


### 6. Prepare for Clean Close

When your window closes, it needs to call `App.close()` to ensure your the
connections to your instruments close properly and that any unsaved data has a
chance to save. You can connect your window's close button to a close function
which will ensure your program exists safely.

<pre><code># Defined in your program class

def close(self):
	print("Closing")
	self.app.close()
</pre></code>

<pre><code># Called where you create your instance of 'ProgramDemo'
app.aboutToQuit.connect(demo_prog.close)
</pre></code>

### 7. Execute Program

To run your program, just call `sys.exit(app.exec_())`!

A complete sample program could look like this:

<pre><code># Import required modules
from PyQt5.QtWidgets import QGridLayout, QWidget
import sys

import hardware_control.backends as hc_back
import hardware_control.gui as hc

# Create class for program
class DemoProgram (hc.MainWindow):
    def __init__(self, app):

        super().__init__(app)

		# Create an oscilloscope backend
        scope_be = hc_back.Keysight_4000X("192.168.0.2")

		# Create an oscilloscope control widget with the backend
        self.scope_wdgt = hc.Oscilloscope(scope_be, self, "Oscilloscope")

        # Create layout, add oscilloscope to row=0, column=0
        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.scope_wdgt, 0, 0)

		# Set 'main_layout' to be displayed
        self.main_widget = QWidget(self)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

		# Indicate the window is ready to show
        self.show()

	#This function guarantees a safe close
    def close(self):
        print("Closing")
        self.app.close()

#This function will create and run the program class
def main():

	# Create a Hardware Control App
    app = hc.App(dummy=True)

	# Create an instance of my class using 'App'
    demo_prog = DemoProgram(app)

	# Connect the window close buttons to the safe close function
    app.aboutToQuit.connect(demo_prog.close)

	# Execute the program
    sys.exit(app.exec_())

#Call the 'main' function
main()
</pre></code>
