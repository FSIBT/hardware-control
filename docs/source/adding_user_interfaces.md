# Add A New User Interface

If there's an instrument type that you would like to use with Hardware Control
but no user interface is available yet, or if you would like to make an alternative
interface to better suit your needs, you can add your own. If you are familiar
with using Qt, it is relatively easy to make a new interface. This guide is designed
to help you through the process of creating a new interface.


### 1. Start with a Template

We would recommend starting by duplicating an existing interface so you can see
exactly which functions you will need to define in your class. This can make the
process of creating a new GUI much smoother.

### 2. Define the GUI

#### GUI Basics

The user interfaces do little more than define a GUI using a series of
widgets.  Usually, this is done entirely within the `__init__()`
function, yet some UIs with repeated structures, such as multi-channel
devices, should define functions or classes in which the widgets for
the repeated structures are created. We would recommend looking at the
Oscilloscope widget as an example of a UI with these repeated
structures.

#### Hardware-Control Widgets

Hardware-Control defines a set of modified widgets to simplify building instrument
interfaces. Examples of such widgets include the `HCPushButton` and `HCLineEdit`,
which extend the standard Qt classes by connecting them to driver command/parameters
names, and automatically registering them within the main app. We recommend using these
widgets (rather than QtWidget objects) since they are pre-configured for reading/setting
instrument parameters and conveying instrument commands.

### 3. Getting Help

Looking at other UIs defined in Hardware Control is by far the quickest way to
learn about building new interfaces. However, please do not hesitate to visit the Qt
documentation or one of the many great Qt tutorials online if you have trouble with
some of the more general Qt GUI building concepts.
