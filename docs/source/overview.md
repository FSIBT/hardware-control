# Overview

Hardware-control is a Python package for controlling laboratory
equipment we most often use in our lab. Specifically, these include
power supplies and scopes and any other instrument that works using
(slow) communication of read and write statements to an instrument.
Hardware that currently will not work well with this code base are,
for example, live streaming cameras or any other instrument that
relies on a fast readout and communication between the program and the
instrument. Also, since we are developing the package to be used for
our experiments, we normally only deal with a moderate amount of
instruments (which can be connected to different computers). If you
want to scale this to hundreds of instruments your mileage may vary ;)

The package has been developed to replace LabVIEW for instrument
control in the [Ion Beam Technology](https://ibt.lbl.gov) group at
[Lawrence Berkeley National Laboratory](https://lbl.gov).

The main goal is to provide easily re-usable user interfaces to
control a wide range of hardware. We try to reduce the amount of code
a user has to write and try to make it easy to combine different
hardware in a single graphical user interface. For example, we try to
provide a single user interface widget for all kind of power supplies.

Furthermore, the program will also run, if one or several of the
instruments are not connected and the program will automatically
detect once an instrument becomes available. To isolate the different
instruments and prevent blocking of the main application, each
instrument is controlled by a separate thread.

Hardware-control consists of several parts:

1. A collection of different instrument drivers. A driver mainly has
   to implement a few functions:

   * A way to create a communication channel to the instrument
   * A list of commands (not all commands the instrument can
     handle need to be implemented). Here the driver will map possible
     commands to a custom name that will be used to access this command.

   In the program, the user will create a python instance of
   a driver for each instrument the user wants to control.

   The actual drivers can rely on different communication protocols,
   e.g. sockets, modbus, usb connection and use different python
   libraries to connect to the instruments, for example,
   [pyvisa](https://pyvisa.readthedocs.io/en/latest/).

   When a user add an instrument driver to the app, the code will
   automatically create a background thread and set up communication
   channels between the main Qt-app and the driver using ZMQ. The
   communication follows a simple ASCII protocol to set and read
   values that gets triggered by the user interacting with the UI or
   by an automated timer. The drivers then translates those requests to the
   actual commands that need to be send to the instrument.

2. A collection of Qt instrument interfaces. Here, several different
   instrument drivers might use the same user interface. This is
   achieved by naming the instrument commands in the different
   instrument drivers consistently.

3. A set of Qt Widgets that can easily access and display data from
   the instruments. For example to easily plot measured values
   vs. time or create logfiles of data that is automatically acquired
   every second.


We try to follow the model-view-controller approach. To achieve this,
we store all the instrument settings and values the instruments report
back in a model in the main app. When an instrument reports a new
value, the value in the model gets updated and the all widgets that
display this value get updated automatically. Widgets that for example
plot data never directly talk to the instrument, but just use the
latest data in the model. This makes the UI responsive, since there
is no delay from the instrument. Instrument data can be automatically
be updated through a timer to keep the model up to date. The downside
of this approach is that the data can be slightly outdated, which, for
our use case, has never been an issue.
