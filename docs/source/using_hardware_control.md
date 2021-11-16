# Write a Control Program

Hardware Control supplies a collection of widgets and instrument drivers for controlling
instruments. This guide will walk you through setting up a simple control
program using Hardware Control.

### 1. Import Hardware Control

Once installed (see installation instructions if you need help), you can import
Hardware Control with the following statement:

    import hardware_control as hc

Now you can access any instrument with `hc.instruments.<instrument_class_name>` and all other
classes, including the user interfaces, with `hc.gui.<class_name>`.

### 2. Create an App Class

Hardware Control uses Qt to create windows and graphics. Qt applications expect
the user to create a class that inherits from QMainWindow. To create your
Hardware Control program, you must also create a class and inherit from
HCMainWindow, Hardware Control's main window class which inherits from QMainWindow. The
class would start off looking like:

    class DemoProgram(hc.HCMainWindow):
        def __init__(self, app):
            super().__init__(app)
            # code to define the GUI


A MainWindow requires a QT-app class object as an argument. HCMainWindow will automatically
create an QT-app class object, but you can also define it explicitly as we will do below.

### 3. Create and Add Instruments

Your program will focus on three main objectives: using instrument drivers to communicate
with instruments, using frontend GUI interfaces that contain widgets and GUI elements
to let you interact with your instrument, and adding these widgets and GUI elements
to the main window.

1. Create an instrument driver

	To create an instrument driver, find the appropriate instrument
	class and initialize it with an instrument name and the physical instrument's
  connection address. The type of address will change depending on the instrument
  class. Most instrument drivers accept IP addresses, but others use alternative
  protocols such as USB, MODBUS or GPIB. You will need to check your instrument's
  documentation to make sure you configure it correctly. We then connect the instrument
  to the main app via the add_instrument function.

            self.app.add_instrument(hc.instruments.Keysight_4000X("scope", "192.168.0.2"))

2. Create a Control Widget

	The control widget or frontend will show the data of the
	instrument to the user and provide controls to change values
	in the instrument. To create the control widget, create an
	class instance of the control widget class and pass the app
	and the name of the instrument to it.

            self.scope_wdgt = hc.gui.Oscilloscope(app, "scope")

3. Add Widget to Layout

	Finally, you must add the control widget to a layout. Qt offers multiple
	ways for arranging layouts, but in this example we will be using
	QGridLayout. To add your widget to a layout, you must create the layout
	object, then use `addWidget()` to add your control widget to the layout
	at the specified position.

             # Create layout, add oscilloscope to row=0, column=0
             self.main_layout = QGridLayout()
             self.main_layout.addWidget(self.scope_wdgt, 0, 0)


Putting together all three steps is how you add an instrument to your
control program. By repeating these steps, you can add multiple
instruments and build complicated control programs with minimal code.

### 4. Prepare your Window to Display

You need to tell your window what to display and when. An easy way to do this is
to create a new QWidget, Qt's base widget class, and set it to use the layout
that contains your control widgets. You can then set this new QWidget to be the
central widget for your main window. The last thing you need to do is add a call to
`self.show()` at the end of your `__init__()` function to tell Qt to display the
window.

    self.main_widget = QWidget(self)
    self.main_widget.setLayout(self.main_layout)
    self.setCentralWidget(self.main_widget)

    self.show()


### 5. Create Instance of Your Class and App

The next step is to create an instance of your class. To do this, you
can pass in an App object. Hardware Control provides it's own version
of an App class which facilitates communication between instruments,
along with a number of other features such as centralized data
collection and menu bars. Create an instance of App and pass it to the
class you defined for your program. Alternatively, the app instance
can also be created automatically if you set `app` to `None`.

    app = hc.App()
    demo_prog = DemoProgram(app)


### 6. Execute Program

To run your program, just call `sys.exit(app.exec_())`!

A complete sample program could look like this:

    # Import required modules
    from PyQt5.QtWidgets import QGridLayout, QWidget
    import sys

    import hardware_control as hc

    # Create class for program
    class DemoProgram(hc.HCMainWindow):
        def __init__(self, app):

            super().__init__(app)

            # Create an oscilloscope instrument driver
            self.app.add_instrument(hc.instruments.Keysight_4000X("scope", "192.168.0.2"))

            # Create an oscilloscope control widget for the instrument
            self.scope_wdgt = hc.gui.Oscilloscope(self.app, "scope")

            # Create layout and add oscilloscope widget to row=0, column=0
            self.main_layout = QGridLayout()
            self.main_layout.addWidget(self.scope_wdgt, 0, 0)

            # Set 'main_layout' to be displayed
            self.main_widget = QWidget(self)
            self.main_widget.setLayout(self.main_layout)
            self.setCentralWidget(self.main_widget)

            # Indicate that the window is ready to show
            self.show()

    # This function will create and run the program class
    if __name__ == "__main__":
      # Create a Hardware Control App
      app = hc.App(dummy=True)  # will always run in dummy mode and not connect to any instrument

      # Create an instance of my class using 'App'
      demo_prog = DemoProgram(app)

      # Execute the program
      sys.exit(app.exec_())

Note that we enforce _dummy_ mode in this program, which enables you
to run and test the program without having the instrument hardware
actually connected to your computer.

You can find more examples on how to use `hardware control` in the
example directory.
