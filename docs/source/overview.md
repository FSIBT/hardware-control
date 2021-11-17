# Overview

Hardware-control is a Python package for controlling laboratory
equipment, a task we do every day in our lab. Specifically, these
include power supplies, scopes, and many other instruments that work
using (slow) communication of read and write statements to an
instrument.  Hardware that currently will not work well with this code
base are, for example, live streaming cameras or any other instrument
that relies on a fast readout and communication between the program
and the instrument. Also, since our use cases are the experiments we
run, we normally only deal with a moderate amount of instruments
(which can be connected to different computers). If you want to scale
this to hundreds of instruments your mileage may vary ;)

The package has been developed to replace LabVIEW for instrument
control in the [Ion Beam Technology](https://ibt.lbl.gov) group at
[Lawrence Berkeley National Laboratory](https://lbl.gov).

The main goal is to provide easily re-usable user interfaces to
control a wide range of hardware. We try to reduce the amount of code
a user has to write and try to make it easy to combine different
hardware in a single graphical user interface. For example, we try to
provide a single user interface widget for all kinds of power supplies.

Furthermore, the program will also run if one or several of the
instruments are not connected, and the program will automatically
detect once an instrument connects. To isolate the different
instruments and prevent blocking of the main application, each
instrument is controlled by a separate thread.

Hardware-control consists of three fundamental parts:

1. A collection of different instrument drivers. A driver mainly has
   to implement a few functions:

   * A way to create a communication channel to the instrument.
   * A list of commands (not all commands the instrument can
     handle need to be implemented). We decided to map each command
     to a custom name, which enables us to write UI controls that
     only rely on these custom names and therefore can be reused
     for different instruments.

   In the program, the user will create a python instance of
   a driver for each instrument the user wants to control.

   The actual drivers can rely on different communication protocols,
   e.g. sockets, modbus, usb connection and use different python
   libraries to connect to the instruments, for example,
   [pyvisa](https://pyvisa.readthedocs.io/en/latest/).

   When a user adds an instrument driver to the app, the code will
   automatically create a background thread and set up communication
   channels between the main Qt-app and the driver using ZMQ. The
   communication follows a simple ASCII protocol to set and read
   values that gets triggered by the user interacting with the UI or
   by an automated timer. The drivers then translate those requests
   into the actual commands that need to be sent to the instrument.

2. A collection of Qt instrument interfaces. Here, several different
   instrument drivers might use the same user interface. This is
   achieved by naming the instrument commands in the different
   instrument drivers consistently.

3. A set of custom Qt Widgets that can easily access and display data from
   the instruments. For example, these can be used to easily plot
   measured values versus time or create logfiles of data that
   are automatically acquired every second. These are basically copies
   of standard Qt Widgets with some extra code that connects, for example,
   the text of a QtLabel to the read value of a parameter in an instrument
   and allows automatic updates by the main app.

We try to follow the model-view-controller approach. To achieve this,
we store all the instrument settings and values the instruments report
in a model in the main app. When an instrument reports a new
value, the value in the model gets updated, and all the widgets that
display this value get updated automatically. Widgets only use the
latest data in the model, and therefore never directly talk to instruments.
This makes the UI responsive since there is no delay from the instrument.
Instrument data can automatically be updated through a timer to keep the
model up to date. The downside of this approach is that the data can be
slightly outdated, which, for our use cases, is not an issue, but might
be for your applications.

We found that this approach makes it easy to write new drivers, while
at the same time keep the flexibility of writing custom Qt applications
with all the features that come with Qt. Providing the same user
interface for different drivers makes it easy to add new instruments
and provide a more uniform interface to the user.
