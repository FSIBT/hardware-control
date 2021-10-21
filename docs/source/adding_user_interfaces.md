# Add A New User Interface

If there's an instrument type you'd like to use with Hardware Control but no
user interface is available yet, or if you'd like to make an alternative
interface to better suit your needs, you can add your own. If you're familiar
with using Qt it is relatively easy to make a new interface. This
step-by-step guide is designed to help walk you through the process of creating
a new interface.


### 1. Start with a Template

Starting by duplicating an existing interface can help you see exactly which
functions you'll need to define in your interface class.

### 2. Define the GUI in` __init__()`

GUIs just inherit from a Qt class, for example, `QGroupBox`.  You then
defined all UI elements inside the `__init__()` function. If you're
creating an interface with repeated elements such as the channel
controls of an oscilloscope, it's recommended to create a class which
implements that subsection of your UI. This makes it easy to change
all of the repeated elements in the future or add and remove them to
the main UI. If you need help with Qt, in addition to the Qt
documentation and tutorials online, you can look at user interfaces
defined in Hardware Control.  One big difference is though that we do
not use Qt's most basic widgets, such as a QPushButton or a QLineEdit
when we want to display an instrument value or control one. Instead we
use Hardware Control's equivalent classes called HCPushButton and
HCLineEdit. These classes extend the standard Qt classes by connecting
them to a specific instrument and parameter/command name. The
HCwidgets also register automatically with the main app, so that when
a new value arrived from an instrument the right widgets are
automatically updated.

